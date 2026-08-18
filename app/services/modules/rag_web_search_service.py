"""时效 Web-Search RAG：Bing API → 摘要 Context → LLM；无 Key 时用样例网页降级。"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.services.modules.rag_prompts import STRICT_WEB
from app.services.shared.llm import chat_completion

_FRESH_HINTS = ("今天", "最新", "近况", "刚刚", "实时", "新闻", "股价", "今日", "本周")

_SAMPLE_PAGES: tuple[dict[str, str], ...] = (
    {
        "title": "样例：开源模型推理成本持续下降",
        "url": "https://example.com/ai/inference-cost",
        "snippet": "多家云厂商本周宣布下调开源大模型推理单价，企业侧 RAG 与客服场景试点加速。",
    },
    {
        "title": "样例：检索增强仍是落地主流路径",
        "url": "https://example.com/ai/rag-adoption",
        "snippet": "分析指出，企业内部知识库问答仍以混合检索 + 拒答约束为主，纯长上下文尚难完全替代。",
    },
    {
        "title": "样例：搜索 API 与时效问答",
        "url": "https://example.com/ai/web-search-rag",
        "snippet": "面向「今天/最新」类问题，业界常见做法是先调搜索引擎 API，再将网页摘要送入 LLM 总结。",
    },
)


def looks_fresh(question: str) -> bool:
    return any(h in (question or "") for h in _FRESH_HINTS)


class RagWebSearchService:
    def _bing_pages(self, q: str, count: int) -> list[dict[str, str]]:
        key = (settings.bing_search_api_key or "").strip()
        if not key:
            return []
        params = {"q": q, "count": min(max(count, 1), 10), "mkt": "zh-CN", "textDecorations": False}
        headers = {"Ocp-Apim-Subscription-Key": key}
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(settings.bing_search_endpoint, params=params, headers=headers)
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Bing 搜索失败: {exc}") from exc
        pages = payload.get("webPages", {}).get("value") or []
        sources: list[dict[str, str]] = []
        for item in pages[:count]:
            sources.append(
                {
                    "title": item.get("name") or "",
                    "url": item.get("url") or "",
                    "snippet": item.get("snippet") or "",
                }
            )
        return sources

    def search_and_answer(self, question: str, *, count: int = 5) -> dict[str, Any]:
        q = (question or "").strip()
        if not q:
            raise HTTPException(status_code=400, detail="问题不能为空")

        key = (settings.bing_search_api_key or "").strip()
        if key:
            sources = self._bing_pages(q, count)
            mode = "bing"
        else:
            sources = [dict(p) for p in _SAMPLE_PAGES[:count]]
            mode = "sample"

        if not sources:
            return {
                "question": q,
                "fresh_hint": looks_fresh(q),
                "search_mode": mode,
                "sources": [],
                "answer": "搜索未返回可用结果，无法根据网页回答。",
            }

        blocks = [
            f"[网页{i}] {s['title']}\nURL: {s['url']}\n摘要: {s['snippet']}"
            for i, s in enumerate(sources, start=1)
        ]
        prefix = ""
        if mode == "sample":
            prefix = "（注意：当前未配置 BING_SEARCH_API_KEY，以下为本地样例网页，仅供演示。）\n"
        answer = chat_completion(
            STRICT_WEB,
            f"{prefix}用户问题：{q}\n\n网页资料：\n" + "\n\n".join(blocks),
            temperature=0.3,
            disable_thinking=True,
            caller="rag.web_search",
        )
        return {
            "question": q,
            "fresh_hint": looks_fresh(q),
            "search_mode": mode,
            "sources": sources,
            "answer": answer,
        }
