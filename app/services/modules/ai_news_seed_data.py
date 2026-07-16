"""AI 资讯导航系统预设（迁移 seed 与运行时只读引用）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class AiNewsPreset(TypedDict):
    slug: str
    url: str
    name: str
    description: str
    region: str
    icon: str
    letter: str
    color: str
    sort_order: int


_BASE = Path(__file__).resolve().parent.parent.parent.parent
_DATA = _BASE / "data" / "ai_news"


def _load_json(name: str):
    return json.loads((_DATA / name).read_text(encoding="utf-8"))


SYSTEM_PRESETS: list[AiNewsPreset] = _load_json("system_presets.json")
_fav = _load_json("default_favorites.json")
DEFAULT_FAVORITE_SLUGS: list[str] = _fav["slugs"]
DEFAULT_FAVORITE_CUSTOM: list[dict[str, str]] = _fav["custom"]
