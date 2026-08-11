"""通用 document_chunks→document_chunk；业务统一 document_business_chunk。

注意：启动时 create_all 可能已先建出空的新表名，需与旧表并存场景兼容。
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.services.modules.chunk_lang import DEFAULT_CHUNK_LANG

logger = logging.getLogger(__name__)

_GENERAL_OLD = "document_chunks"
_GENERAL_NEW = "document_chunk"
_BUSINESS = "document_business_chunk"
_CHUNK_TABLE_RE = re.compile(r"^document_[a-z][a-z0-9_]{0,47}_chunk$")


def _col_names(engine: Engine, table: str) -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns(table)}


def _drop_table_name_unique(conn) -> None:
    conn.execute(text("ALTER TABLE document_corpora DROP CONSTRAINT IF EXISTS document_corpora_table_name_key"))
    conn.execute(text("DROP INDEX IF EXISTS document_corpora_table_name_key"))
    conn.execute(text("DROP INDEX IF EXISTS ix_document_corpora_table_name"))


def _ensure_business_table(conn, engine: Engine, dim: int) -> None:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    tables = set(inspect(engine).get_table_names())
    if _BUSINESS not in tables:
        conn.execute(
            text(
                f"""
                CREATE TABLE {_BUSINESS} (
                    id SERIAL PRIMARY KEY,
                    corpus_name VARCHAR(200) NOT NULL,
                    source_file VARCHAR(500) NOT NULL,
                    section_title VARCHAR(500) NOT NULL DEFAULT '',
                    section_path VARCHAR(500) NOT NULL DEFAULT '',
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    char_count INTEGER NOT NULL,
                    lang VARCHAR(8) NOT NULL DEFAULT '{DEFAULT_CHUNK_LANG}',
                    embedding vector({dim}),
                    search_vector tsvector
                )
                """
            )
        )
    cols = _col_names(engine, _BUSINESS) if _BUSINESS in inspect(engine).get_table_names() else set()
    # create_all 可能已建表但缺列：刷新 inspect
    cols = {c["name"] for c in inspect(engine).get_columns(_BUSINESS)} if _BUSINESS in set(
        inspect(engine).get_table_names()
    ) else cols
    # 事务内新建后需用 conn 侧检查
    cols = set(
        conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                """
            ),
            {"t": _BUSINESS},
        ).scalars()
    )
    if "corpus_name" not in cols:
        conn.execute(
            text(
                f"ALTER TABLE {_BUSINESS} "
                f"ADD COLUMN corpus_name VARCHAR(200) NOT NULL DEFAULT ''"
            )
        )
    if "lang" not in cols:
        conn.execute(
            text(
                f"ALTER TABLE {_BUSINESS} "
                f"ADD COLUMN lang VARCHAR(8) NOT NULL DEFAULT '{DEFAULT_CHUNK_LANG}'"
            )
        )
    if "search_vector" not in cols:
        conn.execute(text(f"ALTER TABLE {_BUSINESS} ADD COLUMN search_vector tsvector"))

    conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_dcc_business_corpus ON {_BUSINESS} (corpus_name)"))
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_dcc_business_src ON {_BUSINESS} (source_file)"))
    conn.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_dcc_business_src_trgm "
            f"ON {_BUSINESS} USING gin (source_file gin_trgm_ops)"
        )
    )
    conn.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_dcc_business_hnsw "
            f"ON {_BUSINESS} USING hnsw (embedding vector_cosine_ops) "
            f"WHERE embedding IS NOT NULL"
        )
    )
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_dcc_business_fts ON {_BUSINESS} USING gin (search_vector)"))


def _migrate_legacy_chunk_table(conn, table: str, corpus_name: str) -> int:
    cols = set(
        conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                """
            ),
            {"t": table},
        ).scalars()
    )
    lang_expr = "lang" if "lang" in cols else f"'{DEFAULT_CHUNK_LANG}'"
    sv_expr = "search_vector" if "search_vector" in cols else "NULL"
    result = conn.execute(
        text(
            f"""
            INSERT INTO {_BUSINESS} (
                corpus_name, source_file, section_title, section_path,
                chunk_index, content, char_count, lang, embedding, search_vector
            )
            SELECT
                :corpus_name, source_file, section_title, section_path,
                chunk_index, content, char_count, {lang_expr}, embedding, {sv_expr}
            FROM {table}
            """
        ),
        {"corpus_name": corpus_name},
    )
    return int(result.rowcount or 0)


def _merge_general_table(conn, engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    # 事务内新建/改名后刷新
    tables = set(
        conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        ).scalars()
    )
    if _GENERAL_OLD not in tables:
        return
    if _GENERAL_NEW not in tables:
        conn.execute(text(f"ALTER TABLE {_GENERAL_OLD} RENAME TO {_GENERAL_NEW}"))
        conn.execute(
            text(
                "ALTER INDEX IF EXISTS ix_document_chunks_embedding_hnsw "
                "RENAME TO ix_document_chunk_embedding_hnsw"
            )
        )
        conn.execute(
            text(
                "ALTER INDEX IF EXISTS ix_document_chunks_source_file_trgm "
                "RENAME TO ix_document_chunk_source_file_trgm"
            )
        )
        logger.info("已重命名 %s → %s", _GENERAL_OLD, _GENERAL_NEW)
        return

    # create_all 已建空 document_chunk：迁入后删旧表
    new_count = int(conn.execute(text(f"SELECT COUNT(*) FROM {_GENERAL_NEW}")).scalar() or 0)
    old_cols = set(
        conn.execute(
            text(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :t
                """
            ),
            {"t": _GENERAL_OLD},
        ).scalars()
    )
    lang_expr = "lang" if "lang" in old_cols else f"'{DEFAULT_CHUNK_LANG}'"
    if new_count == 0:
        conn.execute(
            text(
                f"""
                INSERT INTO {_GENERAL_NEW} (
                    source_file, section_title, section_path, chunk_index,
                    content, char_count, lang, embedding
                )
                SELECT
                    source_file, section_title, section_path, chunk_index,
                    content, char_count, {lang_expr}, embedding
                FROM {_GENERAL_OLD}
                """
            )
        )
        logger.info("已将 %s 数据合并入 %s", _GENERAL_OLD, _GENERAL_NEW)
    else:
        logger.warning(
            "%s 与 %s 同时存在且新表非空，跳过合并，仅删除旧表 %s",
            _GENERAL_OLD,
            _GENERAL_NEW,
            _GENERAL_OLD,
        )
    conn.execute(text(f"DROP TABLE IF EXISTS {_GENERAL_OLD} CASCADE"))


def upgrade(engine: Engine) -> None:
    dim = settings.embedding_dim
    with engine.begin() as conn:
        _merge_general_table(conn, engine)
        _ensure_business_table(conn, engine, dim)

        tables = set(
            conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            ).scalars()
        )
        corpora_map: dict[str, str] = {}
        if "document_corpora" in tables:
            _drop_table_name_unique(conn)
            rows = conn.execute(text("SELECT name, table_name FROM document_corpora")).fetchall()
            corpora_map = {r[1]: r[0] for r in rows}

        legacy = sorted(t for t in tables if _CHUNK_TABLE_RE.match(t) and t != _BUSINESS)
        for table in legacy:
            corpus_name = corpora_map.get(table) or table[len("document_") : -len("_chunk")]
            n = _migrate_legacy_chunk_table(conn, table, corpus_name)
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            logger.info("已迁移并删除旧表 %s → %s（%s 行, corpus=%s）", table, _BUSINESS, n, corpus_name)

        if "document_corpora" in tables:
            # 若共享表此前就是某 corpus 的物理表，补全空 corpus_name
            for old_table, name in corpora_map.items():
                if old_table == _BUSINESS:
                    conn.execute(
                        text(
                            f"UPDATE {_BUSINESS} SET corpus_name = :n "
                            f"WHERE corpus_name = '' OR corpus_name IS NULL"
                        ),
                        {"n": name},
                    )
            conn.execute(text(f"UPDATE document_corpora SET table_name = :t"), {"t": _BUSINESS})
            logger.info("document_corpora.table_name 已统一为 %s", _BUSINESS)
