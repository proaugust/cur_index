"""补全 ai_news_links.created_at 默认值并灌入系统预设（004 已标记但未 seed 时兜底）。"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.services.demo.ai_news_seed_data import SYSTEM_PRESETS

_INSERT = text(
    """
    INSERT INTO ai_news_links (
        user_id, slug, url, name, description, region,
        sort_order, icon, letter, color, is_hidden, created_at
    ) VALUES (
        NULL, :slug, :url, :name, :description, :region,
        :sort_order, :icon, :letter, :color, FALSE, CURRENT_TIMESTAMP
    )
    """
)


def upgrade(engine: Engine) -> None:
    inspector = inspect(engine)
    if "ai_news_links" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE ai_news_links
                ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP
                """
            )
        )

    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM ai_news_links WHERE user_id IS NULL")).scalar() or 0

    if existing:
        return

    with engine.begin() as conn:
        for preset in SYSTEM_PRESETS:
            conn.execute(_INSERT, preset)
