"""将文档切块与投诉 embedding 列统一为 vector(768)（配合 bge-base）。

覆盖：document_chunks、document_*_chunk、complaints、complaint_categories。
维数不符的旧向量置空，需重新导入/向量化。
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.config import settings
from app.services.modules.chunk_table_ops import hnsw_index_name

logger = logging.getLogger(__name__)

_CHUNK_TABLE_RE = re.compile(r"^document_[a-z][a-z0-9_]{0,47}_chunk$")
_TARGET_DIM = 768


def _pg_column_type(engine: Engine, table: str, column: str) -> str | None:
    with engine.connect() as conn:
        return conn.execute(
            text(
                """
                SELECT format_type(a.atttypid, a.atttypmod)
                FROM pg_attribute a
                JOIN pg_class c ON a.attrelid = c.oid
                JOIN pg_namespace n ON c.relnamespace = n.oid
                WHERE n.nspname = 'public'
                  AND c.relname = :table
                  AND a.attname = :column
                  AND a.attnum > 0
                  AND NOT a.attisdropped
                """
            ),
            {"table": table, "column": column},
        ).scalar()


def _migrate_embedding_column(
    engine: Engine,
    table: str,
    *,
    hnsw_index: str | None = None,
) -> None:
    target = f"vector({_TARGET_DIM})"
    current = (_pg_column_type(engine, table, "embedding") or "").lower()
    if current == target:
        logger.info("%s.embedding 已是 %s，跳过改类型", table, target)
        if hnsw_index:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"""
                        CREATE INDEX IF NOT EXISTS {hnsw_index}
                        ON {table} USING hnsw (embedding vector_cosine_ops)
                        WHERE embedding IS NOT NULL
                        """
                    )
                )
        return

    logger.info("%s.embedding 当前=%s → %s", table, current or "unknown", target)
    with engine.begin() as conn:
        if hnsw_index:
            conn.execute(text(f"DROP INDEX IF EXISTS {hnsw_index}"))
        # 维数变更无法就地 cast，旧向量一律清空后改类型
        conn.execute(text(f"UPDATE {table} SET embedding = NULL"))
        conn.execute(
            text(
                f"""
                ALTER TABLE {table}
                ALTER COLUMN embedding TYPE {target}
                USING embedding::{target}
                """
            )
        )
        if hnsw_index:
            conn.execute(
                text(
                    f"""
                    CREATE INDEX IF NOT EXISTS {hnsw_index}
                    ON {table} USING hnsw (embedding vector_cosine_ops)
                    WHERE embedding IS NOT NULL
                    """
                )
            )
    logger.info("已迁移 %s.embedding → %s", table, target)


def upgrade(engine: Engine) -> None:
    if settings.embedding_dim != _TARGET_DIM:
        logger.warning(
            "settings.embedding_dim=%s，本迁移仍按 %s 执行",
            settings.embedding_dim,
            _TARGET_DIM,
        )

    tables = set(inspect(engine).get_table_names())
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    if "document_chunks" in tables:
        _migrate_embedding_column(
            engine,
            "document_chunks",
            hnsw_index="ix_document_chunks_embedding_hnsw",
        )

    for table in sorted(t for t in tables if _CHUNK_TABLE_RE.match(t)):
        _migrate_embedding_column(engine, table, hnsw_index=hnsw_index_name(table))

    for table in ("complaints", "complaint_categories"):
        if table in tables and any(
            c["name"] == "embedding" for c in inspect(engine).get_columns(table)
        ):
            _migrate_embedding_column(engine, table, hnsw_index=None)
