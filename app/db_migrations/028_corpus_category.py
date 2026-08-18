"""document_corpora 增加 category（资料分类，切块表不加）。"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def upgrade(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    if "document_corpora" not in tables:
        return
    with engine.begin() as conn:
        cols = {
            r[0]
            for r in conn.execute(
                text(
                    """
                    SELECT column_name FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = 'document_corpora'
                    """
                )
            )
        }
        if "category" in cols:
            logger.info("document_corpora.category 已存在，跳过")
            return
        conn.execute(
            text(
                """
                ALTER TABLE document_corpora
                ADD COLUMN category VARCHAR(32) NOT NULL DEFAULT 'other'
                """
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_document_corpora_category "
                "ON document_corpora (category)"
            )
        )
    logger.info("已为 document_corpora 增加 category")
