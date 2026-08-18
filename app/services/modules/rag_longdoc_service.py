"""长文档审计演示：细节检索 + 章节聚合摘要上下文。"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud import document_corpora as corpus_crud
from app.services.modules.chunk_lang import detect_lang
from app.services.modules.chunk_table_ops import BUSINESS_CHUNK_TABLE
from app.services.modules.corpus_retrieve import retrieve
from app.services.modules.rag_prompts import STRICT_DOC_QA
from app.services.shared.llm import chat_completion


class RagLongdocService:
    def __init__(self, db: Session):
        self.db = db

    def _require(self, corpus_name: str):
        corpus = corpus_crud.get_corpus_by_name(self.db, corpus_name)
        if corpus is None:
            raise HTTPException(status_code=404, detail=f"资料库不存在: {corpus_name}")
        return corpus

    def analyze(self, corpus_name: str, question: str, *, limit: int = 8) -> dict[str, Any]:
        q = (question or "").strip()
        if not q:
            raise HTTPException(status_code=400, detail="问题不能为空")
        corpus = self._require(corpus_name)
        lang = detect_lang(q)
        try:
            hits = retrieve(
                self.db,
                q,
                table_name=BUSINESS_CHUNK_TABLE,
                corpus_name=corpus.name,
                limit=limit,
                min_similarity=0.35,
                retrieve_mode="hybrid",
                expand_parent=True,
                lang=lang,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        by_section: dict[str, list[str]] = defaultdict(list)
        detail_blocks: list[str] = []
        for i, h in enumerate(hits, start=1):
            path = h.get("section_path") or h.get("section_title") or "正文"
            by_section[path].append(h.get("content") or "")
            detail_blocks.append(
                f"[细节{i}] {h.get('source_file')} · {path}\n{h.get('content')}"
            )

        section_summaries: list[dict[str, str]] = []
        section_blocks: list[str] = []
        for path, parts in list(by_section.items())[:6]:
            merged = "\n".join(parts)[:1200]
            brief = chat_completion(
                "用一两句中文概括以下章节内容，不要添加原文没有的信息。",
                f"章节：{path}\n\n{merged}",
                temperature=0.2,
                disable_thinking=True,
                caller="rag.longdoc.section",
            )
            section_summaries.append({"section_path": path, "summary": brief})
            section_blocks.append(f"[章节摘要] {path}\n{brief}")

        doc_outline = "；".join(s["section_path"] for s in section_summaries) or "（无）"
        user_prompt = (
            f"用户宏观问题：{q}\n\n文档相关章节大纲：{doc_outline}\n\n"
            + "\n\n".join(section_blocks)
            + "\n\n"
            + "\n\n".join(detail_blocks[:6])
            + "\n\n请综合「章节摘要 + 细节」回答；资料不足则明确说明。"
        )
        answer = chat_completion(
            STRICT_DOC_QA + "本题偏宏观审计，注意跨章节风险与义务，勿只复述单段。",
            user_prompt,
            temperature=0.3,
            disable_thinking=True,
            caller="rag.longdoc.answer",
        )
        return {
            "question": q,
            "corpus_name": corpus.name,
            "section_summaries": section_summaries,
            "detail_hits": hits,
            "answer": answer,
        }
