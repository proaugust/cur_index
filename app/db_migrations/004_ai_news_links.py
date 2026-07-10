"""AI 资讯导航：删除旧 prefs 表，改为 ai_news_links 单表。"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.services.modules.ai_news_seed_data import SYSTEM_PRESETS


def upgrade(engine: Engine) -> None:
    inspector = inspect(engine)
    if "ai_news_user_prefs" in inspector.get_table_names():
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS ai_news_user_prefs CASCADE"))

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ai_news_links (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NULL REFERENCES users(id) ON DELETE CASCADE,
                    slug VARCHAR(64) NULL,
                    url TEXT NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    region VARCHAR(20) NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    icon VARCHAR(500) NOT NULL DEFAULT '',
                    letter VARCHAR(8) NOT NULL DEFAULT '',
                    color VARCHAR(16) NOT NULL DEFAULT '#409EFF',
                    is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        # create_all 可能已建表但无 DB 级 DEFAULT，补全以免 INSERT 缺列失败
        conn.execute(
            text(
                """
                ALTER TABLE ai_news_links
                ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP
                """
            )
        )

    existing = 0
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM ai_news_links WHERE user_id IS NULL")).scalar() or 0

    if existing:
        return

    with engine.begin() as conn:
        for preset in SYSTEM_PRESETS:
            conn.execute(
                text(
                    """
                    INSERT INTO ai_news_links (
                        user_id, slug, url, name, description, region,
                        sort_order, icon, letter, color, is_hidden, created_at
                    ) VALUES (
                        NULL, :slug, :url, :name, :description, :region,
                        :sort_order, :icon, :letter, :color, FALSE, CURRENT_TIMESTAMP
                    )
                    """
                ),
                preset,
            )
