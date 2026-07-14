"""业务知识库切块表增加 search_vector（tsvector）+ GIN，并回填。"""

from __future__ import annotations

import logging
import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_CHUNK_TABLE_RE = re.compile(r"^document_[a-z][a-z0-9_]{0,47}_chunk$")


def _gin_index_name(table_name: str) -> str:
    slug = table_name[len("document_") : -len("_chunk")]
    return f"ix_dcc_{slug}_fts"[:63]


def _cjk_spaced(col: str) -> str:
    return f"regexp_replace(coalesce({col}, ''), '([一-龥])', '\\1 ', 'g')"


def _search_vector_expr() -> str:
    title = _cjk_spaced("section_title")
    path = _cjk_spaced("section_path")
    body = _cjk_spaced("content")
    return (
        f"setweight(to_tsvector('simple', {title}), 'A') || "
        f"setweight(to_tsvector('simple', {path}), 'A') || "
        f"setweight(to_tsvector('simple', {body}), 'B')"
    )


def upgrade(engine: Engine) -> None:
    tables = sorted(t for t in inspect(engine).get_table_names() if _CHUNK_TABLE_RE.match(t))
    if not tables:
        return

    expr = _search_vector_expr()
    with engine.begin() as conn:
        for table in tables:
            cols = {c["name"] for c in inspect(engine).get_columns(table)}
            if "search_vector" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN search_vector tsvector"))
                logger.info("已添加 %s.search_vector", table)
            conn.execute(text(f"UPDATE {table} SET search_vector = {expr} WHERE search_vector IS NULL"))
            idx = _gin_index_name(table)
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx} ON {table} USING gin (search_vector)"))
            logger.info("已确保 %s FTS GIN 索引 %s", table, idx)
