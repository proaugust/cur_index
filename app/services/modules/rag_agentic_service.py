"""Agentic RAG：问题拆解 → 多次业务库检索 → 汇总。"""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.modules.agent_common import AgentStepData
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


def _format_hits(hits: list[Any]) -> str:
    if not hits:
        return "未检索到相关片段"
    parts = []
    for h in hits:
        src = h.section_title or h.source_file or ""
        sim = f"{h.similarity:.2f}" if getattr(h, "similarity", None) is not None else "-"
        parts.append(f"[{sim}] {src}\n{(h.content or '')[:240]}")
    return "\n\n".join(parts)


class RagAgenticService:
    def __init__(self, db: Session):
        self.db = db
        self.corpus = CorpusSearchService(db)

    def _plan(self, question: str) -> list[str]:
        plan_raw = chat_completion(
            "将用户复合问题拆成 1-5 个可独立检索的子问题。只输出 JSON 字符串数组，不要其它文字。",
            f"问题：{question}",
            temperature=0.2,
            disable_thinking=True,
            caller="agent.agentic.plan",
        )
        return _parse_steps(plan_raw) or [question]

    def _retrieve(self, corpus_name: str, step: str, *, limit: int) -> tuple[str, list[str]]:
        hits = self.corpus.search(
            corpus_name,
            step,
            limit=limit,
            min_similarity=0.35,
            retrieve_mode="hybrid",
            expand_parent=True,
        )
        ctx = [
            f"子问题「{step}」来源 {h.source_file}\n{h.content}"
            for h in hits
        ]
        return _format_hits(hits), ctx

    def _summarize(self, question: str, steps: list[str], context_parts: list[str]) -> str:
        if not context_parts:
            return "根据现有资料无法确定（各子步骤均未检索到相关片段）。"
        return chat_completion(
            STRICT_AGENT,
            f"原始问题：{question}\n子步骤：{json.dumps(steps, ensure_ascii=False)}\n\n"
            + "\n\n".join(context_parts[:20])
            + "\n\n请按步骤整合最终答复。",
            temperature=0.3,
            disable_thinking=True,
            caller="agent.agentic.answer",
        )

    def run(
        self, corpus_name: str, question: str, *, per_step_limit: int = 3
    ) -> tuple[list[AgentStepData], str]:
        q = (question or "").strip()
        if not q:
            raise HTTPException(status_code=400, detail="问题不能为空")
        if not corpus_name.strip():
            raise HTTPException(status_code=400, detail="请指定业务资料库")

        subqs = self._plan(q)
        out: list[AgentStepData] = [
            AgentStepData(agent="规划 Agent", role="拆分子问题", input=q, output="\n".join(subqs)),
        ]
        context_parts: list[str] = []
        for i, step in enumerate(subqs, start=1):
            text, ctx = self._retrieve(corpus_name, step, limit=per_step_limit)
            context_parts.extend(ctx)
            out.append(
                AgentStepData(
                    agent="检索 Agent",
                    role=f"子问题 {i}",
                    input=step,
                    output=text,
                    meta=corpus_name,
                )
            )
        answer = self._summarize(q, subqs, context_parts)
        out.append(AgentStepData(agent="汇总 Agent", role="最终答复", input=q, output=answer))
        return out, answer
