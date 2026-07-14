"""创建 document_corpora 业务知识库注册表。"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def upgrade(engine: Engine) -> None:
    inspector = inspect(engine)
    if "document_corpora" in inspector.get_table_names():
        logger.info("document_corpora 已存在，跳过创建")
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE document_corpora (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL UNIQUE,
                    table_slug VARCHAR(64) NOT NULL UNIQUE,
                    table_name VARCHAR(80) NOT NULL UNIQUE,
                    default_chunk_strategy VARCHAR(32) NOT NULL DEFAULT 'structure',
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_document_corpora_name ON document_corpora (name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_document_corpora_table_slug ON document_corpora (table_slug)"))
    logger.info("已创建 document_corpora")
