"""document_chunks 向量列维度修正 + HNSW 索引。"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.core.config import settings

logger = logging.getLogger(__name__)


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


def upgrade(engine: Engine) -> None:
    inspector = inspect(engine)
    if "document_chunks" not in inspector.get_table_names():
        return

    dim = settings.embedding_dim
    target = f"vector({dim})"

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    current = (_pg_column_type(engine, "document_chunks", "embedding") or "").lower()
    logger.info("document_chunks.embedding 当前类型: %s，目标: %s", current or "unknown", target)

    with engine.begin() as conn:
        if current != target:
            conn.execute(text("UPDATE document_chunks SET embedding = NULL"))
            conn.execute(
                text(
                    f"""
                    ALTER TABLE document_chunks
                    ALTER COLUMN embedding TYPE {target}
                    USING embedding::{target}
                    """
                )
            )

        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
                ON document_chunks USING hnsw (embedding vector_cosine_ops)
                WHERE embedding IS NOT NULL
                """
            )
        )
