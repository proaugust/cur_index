"""表名改回复数：document_chunk→document_chunks，document_business_chunk→document_business_chunks。"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_RENAMES = (
    ("document_chunk", "document_chunks"),
    ("document_business_chunk", "document_business_chunks"),
)


def _pg_tables(conn) -> set[str]:
    return set(
        conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        ).scalars()
    )


def _rename_table(conn, old: str, new: str, tables: set[str]) -> None:
    if old not in tables:
        logger.info("源表 %s 不存在，跳过", old)
        return
    if new in tables:
        # create_all 可能已建空新表：有数据则合并，否则直接丢掉空壳再 rename
        new_n = int(conn.execute(text(f"SELECT COUNT(*) FROM {new}")).scalar() or 0)
        old_n = int(conn.execute(text(f"SELECT COUNT(*) FROM {old}")).scalar() or 0)
        if new_n == 0 and old_n > 0:
            conn.execute(text(f"DROP TABLE {new} CASCADE"))
            conn.execute(text(f"ALTER TABLE {old} RENAME TO {new}"))
            logger.info("已丢弃空表 %s 并重命名 %s → %s", new, old, new)
        elif old_n == 0:
            conn.execute(text(f"DROP TABLE {old} CASCADE"))
            logger.info("旧表 %s 为空，已删除；保留 %s", old, new)
        else:
            logger.warning("%s 与 %s 均有数据，跳过自动合并，请手工处理", old, new)
        return
    conn.execute(text(f"ALTER TABLE {old} RENAME TO {new}"))
    logger.info("已重命名 %s → %s", old, new)


def upgrade(engine: Engine) -> None:
    with engine.begin() as conn:
        tables = _pg_tables(conn)
        for old, new in _RENAMES:
            _rename_table(conn, old, new, tables)
            tables = _pg_tables(conn)

        if "document_corpora" in tables:
            conn.execute(
                text(
                    "UPDATE document_corpora SET table_name = 'document_business_chunks' "
                    "WHERE table_name IN ('document_business_chunk', 'document_business_chunks')"
                )
            )
            logger.info("document_corpora.table_name 已对齐 document_business_chunks")

        # 通用表索引名（若仍是 025 改过的单数名）
        conn.execute(
            text(
                "ALTER INDEX IF EXISTS ix_document_chunk_embedding_hnsw "
                "RENAME TO ix_document_chunks_embedding_hnsw"
            )
        )
        conn.execute(
            text(
                "ALTER INDEX IF EXISTS ix_document_chunk_source_file_trgm "
                "RENAME TO ix_document_chunks_source_file_trgm"
            )
        )
