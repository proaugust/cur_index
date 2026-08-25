"""通用文档库检索（document_chunks）：vector / hybrid / hybrid_rerank。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import modules as crud
from app.services.modules.chunk_lang import DEFAULT_CHUNK_LANG, detect_lang
from app.services.modules.chunk_table_ops import (
    GENERAL_CHUNK_TABLE,
    apply_gin_previews,
    ensure_chunk_fts,
    row_to_dict,
)
from app.services.modules.corpus_retrieve import retrieve
from app.services.modules.rag_prompts import STRICT_DOC_QA
from app.services.shared.llm import chat_completion

_SYSTEM_PROMPT = STRICT_DOC_QA
_RETRIEVE_MODES = ("vector", "hybrid", "hybrid_rerank")


class DocumentSearchService:
    def __init__(self, db: Session):
        self.db = db

    def _list_recent_chunks(
        self,
        limit: int = 5,
        source_file: str | None = None,
        lang: str | None = None,
    ) -> list[schemas.DocumentChunkSearchResult]:
        chunks, _ = crud.get_document_chunks(
            self.db, source_file=source_file, page=1, page_size=max(limit * 3, limit)
        )
        raw: list[dict] = []
        for chunk in chunks:
            chunk_lang = getattr(chunk, "lang", None) or DEFAULT_CHUNK_LANG
            if lang and chunk_lang != lang:
                continue
            raw.append({**row_to_dict(chunk), "similarity": 0.0})
            if len(raw) >= limit:
                break
        apply_gin_previews(self.db, GENERAL_CHUNK_TABLE, raw)
        return [schemas.DocumentChunkSearchResult(**item) for item in raw]

    def search(
        self,
        query: str | None,
        limit: int = 5,
        source_file: str | None = None,
        min_similarity: float = 0.55,
        retrieve_mode: str = "hybrid_rerank",
        expand_parent: bool = False,
    ) -> list[schemas.DocumentChunkSearchResult]:
        mode = (retrieve_mode or "hybrid_rerank").strip().lower()
        if mode not in _RETRIEVE_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"retrieve_mode 仅支持: {', '.join(_RETRIEVE_MODES)}",
            )
        ensure_chunk_fts(self.db, GENERAL_CHUNK_TABLE)
        if not query or not query.strip():
            return self._list_recent_chunks(limit=limit, source_file=source_file)

        resolved_lang = detect_lang(query)
        try:
            items = retrieve(
                self.db,
                query.strip(),
                table_name=GENERAL_CHUNK_TABLE,
                limit=limit,
                min_similarity=min_similarity,
                source_file=source_file,
                retrieve_mode=mode,
                expand_parent=expand_parent,
                lang=resolved_lang,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [schemas.DocumentChunkSearchResult(**item) for item in items]

    def search_polished(
        self,
        query: str | None,
        limit: int = 5,
        min_similarity: float = 0.55,
        retrieve_mode: str = "hybrid",
        expand_parent: bool = True,
    ) -> schemas.DocumentSearchPolishedResult:
        sources = self.search(
            query,
            limit=limit,
            min_similarity=min_similarity,
            retrieve_mode=retrieve_mode,
            expand_parent=expand_parent,
        )
        if not query or not query.strip():
            original_sources = [
                schemas.DocumentSearchPolishedSource.from_search_hit(
                    index,
                    chunk,
                    f"{chunk.source_file} · {chunk.section_title or chunk.section_path or '正文'}",
                )
                for index, chunk in enumerate(sources, start=1)
            ]
            return schemas.DocumentSearchPolishedResult(
                query="",
                polished_answer=f"未提供查询文本，以下为库中前 {len(sources)} 条切块。",
                source_count=len(original_sources),
                original_sources=original_sources,
            )

        if not sources:
            return schemas.DocumentSearchPolishedResult(
                query=query, polished_answer="未检索到相关文档片段，无法生成回答。", source_count=0, original_sources=[]
            )

        context_blocks = []
        original_sources: list[schemas.DocumentSearchPolishedSource] = []
        for index, chunk in enumerate(sources, start=1):
            header = chunk.section_title or chunk.section_path or "正文"
            source_label = f"{chunk.source_file} · {header}"
            context_blocks.append(f"[片段{index}] 来源: {source_label}\n{chunk.content}")
            original_sources.append(
                schemas.DocumentSearchPolishedSource.from_search_hit(index, chunk, source_label)
            )

        user_prompt = (
            f"用户问题：{query}\n\n共检索到 {len(sources)} 条相关片段，请综合后回答：\n\n"
            + "\n\n".join(context_blocks)
        )
        polished_answer = chat_completion(
            _SYSTEM_PROMPT, user_prompt, temperature=0.5, disable_thinking=True, caller="rag.search_and_llm"
        )
        return schemas.DocumentSearchPolishedResult(
            query=query,
            polished_answer=polished_answer,
            source_count=len(original_sources),
            original_sources=original_sources,
        )
