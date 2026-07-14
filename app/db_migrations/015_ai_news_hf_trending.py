"""将 Hugging Face Papers 系统预设更新为 Trending 地址。"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade(engine: Engine) -> None:
    inspector = inspect(engine)
    if "ai_news_links" not in inspector.get_table_names():
        return

    params = {
        "url": "https://huggingface.co/papers/trending",
        "name": "Hugging Face Trending Papers",
        "description": "社区热门 AI 论文榜单",
    }
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE ai_news_links
                SET url = :url,
                    name = :name,
                    description = :description
                WHERE slug = 'huggingfacePapers'
                """
            ),
            params,
        )
