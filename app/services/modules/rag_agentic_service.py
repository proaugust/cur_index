"""Agentic RAG：问题拆解 → 多次业务库检索 → 汇总。"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.modules.corpus_search_service import CorpusSearchService
from app.services.modules.rag_prompts import STRICT_AGENT
from app.services.shared.llm import chat_completion


def _parse_steps(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x).strip() for x in data if str(x).strip()][:5]
    except json.JSONDecodeError:
        pass
    lines = []
    for line in raw.splitlines():
        m = re.match(r"^\s*(?:\d+[\.\)、]|[-*])\s*(.+)$", line)
        if m:
            lines.append(m.group(1).strip())
    if lines:
        return lines[:5]
    text = raw.strip()
    return [text] if text else []


class RagAgenticService:
    def __init__(self, db: Session):
        self.db = db
        self.corpus = CorpusSearchService(db)

    def run(self, corpus_name: str, question: str, *, per_step_limit: int = 3) -> dict[str, Any]:
        q = (question or "").strip()
        if not q:
            raise HTTPException(status_code=400, detail="问题不能为空")
        if not corpus_name.strip():
            raise HTTPException(status_code=400, detail="请指定业务资料库")

        plan_raw = chat_completion(
            "将用户复合问题拆成 1-5 个可独立检索的子问题。只输出 JSON 字符串数组，不要其它文字。",
            f"问题：{q}",
            temperature=0.2,
            disable_thinking=True,
            caller="rag.agentic.plan",
        )
        steps = _parse_steps(plan_raw)
        if not steps:
            steps = [q]

        step_results: list[dict[str, Any]] = []
        context_parts: list[str] = []
        for i, step in enumerate(steps, start=1):
            hits = self.corpus.search(
                corpus_name,
                step,
                limit=per_step_limit,
                min_similarity=0.35,
                retrieve_mode="hybrid",
                expand_parent=True,
            )
            snippets = []
            for j, h in enumerate(hits, start=1):
                snippets.append(
                    {
                        "id": h.id,
                        "source_file": h.source_file,
                        "section_title": h.section_title,
                        "content": h.content,
                        "similarity": h.similarity,
                    }
                )
                context_parts.append(
                    f"[步骤{i}.{j}] 子问题「{step}」来源 {h.source_file}\n{h.content}"
                )
            step_results.append({"step": step, "hits": snippets})

        if not context_parts:
            return {
                "question": q,
                "corpus_name": corpus_name,
                "steps": steps,
                "step_results": step_results,
                "answer": "根据现有资料无法确定（各子步骤均未检索到相关片段）。",
            }

        answer = chat_completion(
            STRICT_AGENT,
            f"原始问题：{q}\n子步骤：{json.dumps(steps, ensure_ascii=False)}\n\n"
            + "\n\n".join(context_parts[:20])
            + "\n\n请按步骤整合最终答复。",
            temperature=0.3,
            disable_thinking=True,
            caller="rag.agentic.answer",
        )
        return {
            "question": q,
            "corpus_name": corpus_name,
            "steps": steps,
            "step_results": step_results,
            "answer": answer,
        }
