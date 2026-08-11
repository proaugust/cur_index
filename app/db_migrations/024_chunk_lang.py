"""仅为 document_corpora / document_chunks / document_fastapi_chunk 增加 lang。

切块表若有 search_vector，则按 lang 重算 FTS 分词。
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.services.modules.chunk_lang import CHUNK_LANGS, DEFAULT_CHUNK_LANG, search_vector_sql_expr

logger = logging.getLogger(__name__)

# 仅这三张表
_TARGETS = ("document_corpora", "document_chunks", "document_fastapi_chunk")


def _column_names(conn, table: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = :t
            """
        ),
        {"t": table},
    )
    return {r[0] for r in rows}


def upgrade(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    targets = [t for t in _TARGETS if t in tables]
    if not targets:
        return

    with engine.begin() as conn:
        for table in targets:
            conn.execute(
                text(
                    f"""
                    ALTER TABLE {table}
                    ADD COLUMN IF NOT EXISTS lang VARCHAR(8) NOT NULL DEFAULT '{DEFAULT_CHUNK_LANG}'
                    """
                )
            )
            logger.info("已确保 %s.lang", table)

        # 仅物理切块表重算 FTS（document_corpora 无 search_vector）
        for table in targets:
            if table == "document_corpora":
                continue
            cols = _column_names(conn, table)
            if "search_vector" not in cols:
                continue
            for lang in CHUNK_LANGS:
                expr = search_vector_sql_expr(lang)
                conn.execute(
                    text(f"UPDATE {table} SET search_vector = {expr} WHERE lang = :lang"),
                    {"lang": lang},
                )
            logger.info("已按 lang 重算 %s.search_vector", table)
