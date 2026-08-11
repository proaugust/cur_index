"""切块表 source_file 增加 pg_trgm GIN 索引，加速 RAG 按文件名 ILIKE 过滤。"""

from __future__ import annotations

import logging
import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_CHUNK_TABLE_RE = re.compile(r"^document_[a-z][a-z0-9_]{0,47}_chunk$")


def _trgm_index_name(table_name: str) -> str:
    slug = table_name[len("document_") : -len("_chunk")]
    return f"ix_dcc_{slug}_src_trgm"[:63]


def _ensure_trgm_index(conn, table_name: str) -> None:
    idx = _trgm_index_name(table_name)
    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx} ON {table_name} USING gin (source_file gin_trgm_ops)"))
    logger.info("已确保 %s source_file GIN(trgm) 索引 %s", table_name, idx)


def upgrade(engine: Engine) -> None:
    tables = sorted(t for t in inspect(engine).get_table_names() if _CHUNK_TABLE_RE.match(t))
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        for table in tables:
            cols = {c["name"] for c in inspect(engine).get_columns(table)}
            if "source_file" in cols:
                _ensure_trgm_index(conn, table)
        if "document_chunks" in inspect(engine).get_table_names():
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_document_chunks_source_file_trgm
                    ON document_chunks USING gin (source_file gin_trgm_ops)
                    """
                )
            )
            logger.info("已确保 document_chunks source_file GIN(trgm) 索引")
