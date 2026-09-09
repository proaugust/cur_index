"""切块表 document_chunks / document_business_chunks 的建表 / FTS / HNSW 辅助。

表结构与索引维护只应在进程启动（或迁移）跑一次；检索路径禁止调用 ensure_*。
导入/改切块只做 scoped 的 refresh_search_vectors。
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from typing import Any

from sqlalchemy import bindparam, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.modules.chunk_lang import (
    CHUNK_LANGS,
    DEFAULT_CHUNK_LANG,
    search_vector_sql_expr,
)

logger = logging.getLogger(__name__)

BUSINESS_CHUNK_TABLE = "document_business_chunks"
GENERAL_CHUNK_TABLE = "document_chunks"
_CHUNK_TABLES = frozenset({BUSINESS_CHUNK_TABLE, GENERAL_CHUNK_TABLE})

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
HNSW_BULK_THRESHOLD = 500

_schema_lock = threading.Lock()
_schema_ready = False


def _require_chunk_table(table_name: str) -> str:
    if table_name not in _CHUNK_TABLES:
        raise ValueError(f"切块表仅支持 {sorted(_CHUNK_TABLES)}，收到: {table_name}")
    return table_name


def hnsw_index_name(table_name: str = BUSINESS_CHUNK_TABLE) -> str:
    if table_name == BUSINESS_CHUNK_TABLE:
        return "ix_dcc_business_hnsw"
    if table_name == GENERAL_CHUNK_TABLE:
        return "ix_document_chunks_embedding_hnsw"
    return f"ix_dcc_{table_name}_hnsw"[:63]

def fts_index_name(table_name: str = BUSINESS_CHUNK_TABLE) -> str:
    if table_name == BUSINESS_CHUNK_TABLE:
        return "ix_dcc_business_fts"
    if table_name == GENERAL_CHUNK_TABLE:
        return "ix_document_chunks_fts"
    return f"ix_dcc_{table_name}_fts"[:63]

def source_file_like_pattern(pattern: str | None) -> str | None:
    """无通配符时按子串匹配；含 % / _ 时按 SQL LIKE 语义。"""
    if not pattern or not pattern.strip():
        return None
    p = pattern.strip()
    if "%" in p or "_" in p:
        return p
    return f"%{p}%"


def name_to_slug(name: str) -> str:
    raw = name.strip().lower()
    ascii_part = re.sub(r"[^a-z0-9]+", "_", raw)
    ascii_part = re.sub(r"_+", "_", ascii_part).strip("_")
    if ascii_part and _SLUG_RE.match(ascii_part):
        return ascii_part[:48]
    digest = hashlib.sha1(name.strip().encode("utf-8")).hexdigest()[:10]
    if ascii_part:
        base = re.sub(r"[^a-z0-9_]", "", ascii_part)[:30].strip("_")
        candidate = f"{base}_{digest[:4]}" if base else f"c_{digest}"
    else:
        candidate = f"c_{digest}"
    if not candidate[0].isalpha():
        candidate = f"c_{candidate}"
    return candidate[:48]


def table_name_for_slug(_slug: str) -> str:
    """业务库统一物理表（保留函数签名兼容注册逻辑）。"""
    return BUSINESS_CHUNK_TABLE


def _create_hnsw_sql(table_name: str = BUSINESS_CHUNK_TABLE) -> str:
    return (
        f"CREATE INDEX IF NOT EXISTS {hnsw_index_name(table_name)} "
        f"ON {table_name} USING hnsw (embedding vector_cosine_ops) "
        f"WHERE embedding IS NOT NULL"
    )


def _create_fts_sql(table_name: str = BUSINESS_CHUNK_TABLE) -> str:
    return (
        f"CREATE INDEX IF NOT EXISTS {fts_index_name(table_name)} "
        f"ON {table_name} USING gin (search_vector)"
    )


def _src_trgm_index_name(table_name: str) -> str:
    if table_name == BUSINESS_CHUNK_TABLE:
        return "ix_dcc_business_src_trgm"
    return "ix_document_chunks_source_file_trgm"


def _ensure_business_table(conn, dim: int) -> None:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    conn.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {BUSINESS_CHUNK_TABLE} (
                id SERIAL PRIMARY KEY,
                corpus_name VARCHAR(200) NOT NULL,
                source_file VARCHAR(500) NOT NULL,
                section_title VARCHAR(500) NOT NULL DEFAULT '',
                section_path VARCHAR(500) NOT NULL DEFAULT '',
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                char_count INTEGER NOT NULL,
                lang VARCHAR(8) NOT NULL DEFAULT '{DEFAULT_CHUNK_LANG}',
                original_import_path VARCHAR(1000),
                embedding vector({dim}),
                search_vector tsvector
            )
            """
        )
    )
    conn.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_dcc_business_corpus "
            f"ON {BUSINESS_CHUNK_TABLE} (corpus_name)"
        )
    )
    conn.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS ix_dcc_business_src "
            f"ON {BUSINESS_CHUNK_TABLE} (source_file)"
        )
    )


def _patch_chunk_columns(conn, table: str, cols: set[str]) -> None:
    if table == BUSINESS_CHUNK_TABLE and "corpus_name" not in cols:
        conn.execute(
            text(
                f"ALTER TABLE {table} "
                f"ADD COLUMN corpus_name VARCHAR(200) NOT NULL DEFAULT ''"
            )
        )
    if "lang" not in cols:
        conn.execute(
            text(
                f"ALTER TABLE {table} "
                f"ADD COLUMN lang VARCHAR(8) NOT NULL DEFAULT '{DEFAULT_CHUNK_LANG}'"
            )
        )
        logger.info("已为 %s 添加 lang", table)
    if "original_import_path" not in cols:
        conn.execute(
            text(f"ALTER TABLE {table} ADD COLUMN original_import_path VARCHAR(1000)")
        )
        logger.info("已为 %s 添加 original_import_path", table)
    if "search_vector" not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN search_vector tsvector"))
        logger.info("已为 %s 添加 search_vector", table)


def _backfill_null_search_vectors(conn, table: str) -> None:
    for lang in CHUNK_LANGS:
        expr = search_vector_sql_expr(lang)
        conn.execute(
            text(
                f"UPDATE {table} SET search_vector = {expr} "
                f"WHERE search_vector IS NULL AND lang = :lang"
            ),
            {"lang": lang},
        )


def _ensure_chunk_indexes(conn, table: str) -> None:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    conn.execute(
        text(
            f"CREATE INDEX IF NOT EXISTS {_src_trgm_index_name(table)} "
            f"ON {table} USING gin (source_file gin_trgm_ops)"
        )
    )
    conn.execute(text(_create_hnsw_sql(table)))
    conn.execute(text(_create_fts_sql(table)))


def ensure_chunk_schemas(engine: Engine) -> None:
    """进程内只执行一次：补齐两张切块表的列 / 索引，并回填 NULL search_vector。"""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        dim = settings.embedding_dim
        if BUSINESS_CHUNK_TABLE not in inspect(engine).get_table_names():
            with engine.begin() as conn:
                _ensure_business_table(conn, dim)
            logger.info("已创建切块表 %s", BUSINESS_CHUNK_TABLE)
        with engine.begin() as conn:
            tables = set(inspect(engine).get_table_names())
            for table in (GENERAL_CHUNK_TABLE, BUSINESS_CHUNK_TABLE):
                if table not in tables:
                    continue
                cols = {c["name"] for c in inspect(engine).get_columns(table)}
                _patch_chunk_columns(conn, table, cols)
                _backfill_null_search_vectors(conn, table)
                _ensure_chunk_indexes(conn, table)
        _schema_ready = True
        logger.info("切块表 schema 已就绪（仅本次进程启动）")


def ensure_chunk_table(db: Session, table_name: str = BUSINESS_CHUNK_TABLE) -> None:
    """兼容旧调用：转交进程级一次性 ensure_chunk_schemas。检索路径勿再调用。"""
    if table_name != BUSINESS_CHUNK_TABLE:
        raise ValueError(f"业务切块仅支持固定表 {BUSINESS_CHUNK_TABLE}，收到: {table_name}")
    ensure_chunk_schemas(db.get_bind())


def ensure_chunk_lang(db: Session, table_name: str = BUSINESS_CHUNK_TABLE) -> None:
    ensure_chunk_schemas(db.get_bind())


def ensure_chunk_fts(db: Session, table_name: str = BUSINESS_CHUNK_TABLE) -> None:
    """兼容旧调用：不再在热路径做全表维护，仅保证启动级 schema 已执行。"""
    _require_chunk_table(table_name)
    ensure_chunk_schemas(db.get_bind())


def ensure_chunk_source_file_trgm(db: Session, table_name: str = BUSINESS_CHUNK_TABLE) -> None:
    ensure_chunk_schemas(db.get_bind())


def refresh_search_vectors(
    db: Session,
    table_name: str = BUSINESS_CHUNK_TABLE,
    *,
    source_files: list[str] | None = None,
    corpus_name: str | None = None,
) -> None:
    table = _require_chunk_table(table_name)
    for lang in CHUNK_LANGS:
        expr = search_vector_sql_expr(lang)
        clauses = ["lang = :lang"]
        params: dict[str, Any] = {"lang": lang}
        if corpus_name and table == BUSINESS_CHUNK_TABLE:
            clauses.append("corpus_name = :corpus_name")
            params["corpus_name"] = corpus_name
        if source_files:
            clauses.append("source_file IN :files")
            stmt = text(
                f"UPDATE {table} SET search_vector = {expr} WHERE {' AND '.join(clauses)}"
            ).bindparams(bindparam("files", expanding=True))
            params["files"] = list(source_files)
            db.execute(stmt, params)
        else:
            clauses.append("search_vector IS NULL")
            db.execute(
                text(f"UPDATE {table} SET search_vector = {expr} WHERE {' AND '.join(clauses)}"),
                params,
            )


def drop_hnsw_index(db: Session, table_name: str = BUSINESS_CHUNK_TABLE) -> None:
    table = _require_chunk_table(table_name)
    db.execute(text(f"DROP INDEX IF EXISTS {hnsw_index_name(table)}"))


def create_hnsw_index(db: Session, table_name: str = BUSINESS_CHUNK_TABLE) -> None:
    table = _require_chunk_table(table_name)
    db.execute(text(_create_hnsw_sql(table)))


def get_chunk_model(table_name: str = BUSINESS_CHUNK_TABLE):
    """返回切块 ORM（通用 / 业务固定表）。"""
    table = _require_chunk_table(table_name)
    from app import models
    if table == GENERAL_CHUNK_TABLE:
        return models.DocumentChunk
    return models.DocumentBusinessChunk

def embedding_preview(embedding: Any, *, head: int = 4) -> str | None:
    """前几维 + 总维数。"""
    if embedding is None:
        return None
    try:
        vals = list(embedding)
    except TypeError:
        return None
    if not vals:
        return None
    head_s = ", ".join(f"{float(x):.3f}" for x in vals[:head])
    return f"[{head_s}, …] ×{len(vals)}"

def chunk_embed_text(*, section_path: str, section_title: str, content: str) -> str:
    prefix = (section_path or section_title or "").strip()
    return f"[{prefix}] {content}" if prefix else content

def row_to_dict(row: Any) -> dict[str, Any]:
    from sqlalchemy import inspect as sa_inspect

    state = sa_inspect(row)
    emb_preview = None
    if "embedding" not in state.unloaded:
        emb_preview = embedding_preview(getattr(row, "embedding", None))
    return {
        "id": row.id,
        "source_file": row.source_file,
        "section_title": row.section_title,
        "section_path": row.section_path,
        "chunk_index": row.chunk_index,
        "content": row.content,
        "char_count": row.char_count,
        "lang": getattr(row, "lang", None) or DEFAULT_CHUNK_LANG,
        "embedding_preview": emb_preview,
    }

def gin_preview(from_fts: bool = False, fts_rank: float = 0.0, *, sv_text: str | None = None) -> str:
    snip = (sv_text or "").strip()
    snip = snip[:56] + "…" if len(snip) > 56 else snip
    if from_fts:
        return f"命中 {fts_rank:.4f}" + (f" · {snip}" if snip else "")
    return snip or "—"

def apply_gin_previews(db: Session, table_name: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ids = [int(it["id"]) for it in items if it.get("id") is not None]
    snips: dict[int, str] = {}
    if ids:
        table = _require_chunk_table(table_name)
        stmt = text(
            f"SELECT id, left(search_vector::text, 72) AS s FROM {table} WHERE id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        for r in db.execute(stmt, {"ids": ids}):
            snips[int(r.id)] = r.s or ""
    for it in items:
        cid = int(it["id"])
        it["gin_preview"] = gin_preview(
            bool(it.get("from_fts")), float(it.get("fts_rank") or 0), sv_text=snips.get(cid)
        )
    return items
