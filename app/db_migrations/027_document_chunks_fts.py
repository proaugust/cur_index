"""通用文档库 document_chunks 增加 search_vector（tsvector）+ GIN，并按 lang 回填。"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.services.modules.chunk_lang import CHUNK_LANGS, search_vector_sql_expr

logger = logging.getLogger(__name__)

_TABLE = "document_chunks"
_FTS_INDEX = "ix_document_chunks_fts"


def upgrade(engine: Engine) -> None:
    if _TABLE not in inspect(engine).get_table_names():
        return

    cols = {c["name"] for c in inspect(engine).get_columns(_TABLE)}
    with engine.begin() as conn:
        if "search_vector" not in cols:
            conn.execute(text(f"ALTER TABLE {_TABLE} ADD COLUMN search_vector tsvector"))
            logger.info("已添加 %s.search_vector", _TABLE)

        for lang in CHUNK_LANGS:
            expr = search_vector_sql_expr(lang)
            conn.execute(
                text(f"UPDATE {_TABLE} SET search_vector = {expr} WHERE search_vector IS NULL AND lang = :lang"),
                {"lang": lang},
            )

        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {_FTS_INDEX} ON {_TABLE} USING gin (search_vector)"))
        logger.info("已确保 %s FTS GIN 索引 %s", _TABLE, _FTS_INDEX)
