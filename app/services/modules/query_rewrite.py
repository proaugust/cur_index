"""搜索 + LLM 检索前改写：把口语问题补全或拆成至多 3 条检索查询。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services.shared.llm import chat_completion

logger = logging.getLogger(__name__)

_SYSTEM = (
    "你是检索查询改写器。把用户问题改写成 1 到 3 条适合文档检索的短查询："
    "补全省略的主语，并列问题拆开。不要回答问题。"
    "只输出 JSON 数组，例如 [\"查询1\",\"查询2\"]。"
)


def _parse_queries(raw: str) -> list[str]:
    text = (raw or "").strip()
    if not text:
        return []
    data: Any
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\[[\s\S]*\]", text)
        if not match:
            return []
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return []
    if isinstance(data, dict):
        data = data.get("queries") or data.get("query") or []
    if isinstance(data, str):
        data = [data]
    if not isinstance(data, list):
        return []
    out: list[str] = []
    for item in data:
        query = str(item).strip()
        if query and query not in out:
            out.append(query)
    return out[:3]


def rewrite_queries(question: str) -> list[str]:
    """原问题始终在首位。改写失败时只返回原问题。"""
    query = question.strip()
    if not query:
        return []
    try:
        raw = chat_completion(
            _SYSTEM,
            query,
            temperature=0,
            disable_thinking=True,
            caller="rag.query_rewrite",
        )
    except Exception:
        logger.warning("查询改写失败，使用原问题", exc_info=True)
        return [query]
    out = [query]
    for item in _parse_queries(raw):
        if item not in out:
            out.append(item)
        if len(out) >= 3:
            break
    return out


def merge_scored(groups: list[list[Any]], limit: int) -> list[Any]:
    """按 id 合并多路检索，保留相似度更高的一条。"""
    best: dict[tuple[str, Any], Any] = {}
    for group in groups:
        for item in group:
            key = (getattr(item, "corpus_name", None) or "", getattr(item, "id", None))
            prev = best.get(key)
            score = float(getattr(item, "similarity", 0) or 0)
            if prev is None or score > float(getattr(prev, "similarity", 0) or 0):
                best[key] = item
    ranked = sorted(best.values(), key=lambda row: float(getattr(row, "similarity", 0) or 0), reverse=True)
    return ranked[:limit]
