"""将 document_chunks / document_*_chunk 的 section_title、section_path 加宽为 VARCHAR(500)。"""

from __future__ import annotations

import logging
import re

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

_CHUNK_TABLE_RE = re.compile(r"^document_[a-z][a-z0-9_]{0,47}_chunk$")
_TARGET_COLS = ("section_title", "section_path")


def _needs_widen(engine: Engine, table: str, column: str) -> bool:
    for col in inspect(engine).get_columns(table):
        if col["name"] != column:
            continue
        typ = col.get("type")
        length = getattr(typ, "length", None)
        return length is not None and length < 500
    return False


def upgrade(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    targets = sorted(
        t for t in tables if t == "document_chunks" or _CHUNK_TABLE_RE.match(t)
    )
    alters = [
        (table, column)
        for table in targets
        for column in _TARGET_COLS
        if _needs_widen(engine, table, column)
    ]
    if not alters:
        return

    with engine.begin() as conn:
        for table, column in alters:
            conn.execute(
                text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(500)")
            )
            logger.info("已加宽 %s.%s -> VARCHAR(500)", table, column)
