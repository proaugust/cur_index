"""业务知识库向量检索（document_business_chunks，按 corpus_name / 多库过滤）。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import document_corpora as corpus_crud
from app.services.modules.chunk_lang import detect_lang
from app.services.modules.chunk_table_ops import (
    BUSINESS_CHUNK_TABLE,
    apply_gin_previews,
    ensure_chunk_table,
    row_to_dict,
)
from app.services.modules.corpus_retrieve import retrieve
from app.services.modules.corpus_search_filters import (
    normalize_category_list,
    resolve_corpus_names,
    suggest_search_filters,
)
from app.services.modules.rag_prompts import STRICT_DOC_QA
from app.services.shared.llm import chat_completion

_SYSTEM_PROMPT = STRICT_DOC_QA
_RETRIEVE_MODES = ("vector", "hybrid", "hybrid_rerank")

_REWRITE_SYSTEM = (
    "你是检索查询优化助手。将用户问题改写为更适合文档检索的关键词组合。"
    "要求：保留核心意图；补充专业同义词/上下位词；去掉口语化表达；"
    "输出仅一行改写后的查询，不要解释，不要标点符号开头。"
)


def _rewrite_query(query: str) -> str:
    """用 LLM 改写查询以提升向量/全文召回率；失败时静默回退到原 query。"""
    try:
        rewritten = chat_completion(
            _REWRITE_SYSTEM,
            query,
            temperature=0.0,
            disable_thinking=True,
            caller="rag.query_rewrite",
        )
        rewritten = rewritten.strip().splitlines()[0].strip()
        return rewritten if rewritten else query
    except Exception:
        return query


class CorpusSearchService:
    def __init__(self, db: Session):
        self.db = db

    def _require_corpus(self, corpus_name: str):
        ensure_chunk_table(self.db, BUSINESS_CHUNK_TABLE)
        corpus = corpus_crud.get_corpus_by_name(self.db, corpus_name)
        if corpus is None:
            raise HTTPException(status_code=404, detail=f"资料库不存在: {corpus_name}")
        if corpus.table_name != BUSINESS_CHUNK_TABLE:
            corpus.table_name = BUSINESS_CHUNK_TABLE
            self.db.commit()
            self.db.refresh(corpus)
        return corpus

    def suggest_filters(self, question: str) -> schemas.CorpusSearchFiltersSuggest:
        ensure_chunk_table(self.db, BUSINESS_CHUNK_TABLE)
        return schemas.CorpusSearchFiltersSuggest(**suggest_search_filters(self.db, question))

    def list_files(self, corpus_name: str | None) -> schemas.CorpusFileListResult:
        ensure_chunk_table(self.db, BUSINESS_CHUNK_TABLE)
        resolved_name = self._require_corpus(corpus_name).name if corpus_name else None
        rows = corpus_crud.list_source_files(self.db, resolved_name)
        files = [
            schemas.CorpusFileItem(
                source_file=source_file,
                corpus_name=name if resolved_name is None else None,
            )
            for name, source_file in rows
        ]
        return schemas.CorpusFileListResult(
            corpus_name=resolved_name,
            table_name=BUSINESS_CHUNK_TABLE,
            files=files,
        )

    def list_by_file(
        self,
        corpus_name: str | None,
        source_file: str | None = None,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> schemas.SourceFileListPage:
        ensure_chunk_table(self.db, BUSINESS_CHUNK_TABLE)
        resolved_name = self._require_corpus(corpus_name).name if corpus_name else None
        rows, total = corpus_crud.list_source_files_page(
            self.db,
            resolved_name,
            source_file=source_file,
            page=page,
            page_size=page_size,
        )
        items = [
            schemas.SourceFileItem(
                source_file=path,
                corpus_name=name if resolved_name is None else None,
            )
            for name, path in rows
        ]
        return schemas.SourceFileListPage(
            items=items, total=total, page=page, page_size=page_size
        )

    def _list_recent(self, corpus_names: list[str] | None, limit: int, source_file: str | None):
        rows, _ = corpus_crud.list_chunks(
            self.db,
            None,
            source_file=source_file,
            corpus_names=corpus_names,
            page=1,
            page_size=limit,
        )
        raw = [{**row_to_dict(row), "similarity": 0.0} for row in rows]
        apply_gin_previews(self.db, BUSINESS_CHUNK_TABLE, raw)
        return [schemas.DocumentChunkSearchResult(**item) for item in raw]

    def search(
        self,
        corpus_name: str | None,
        query: str | None,
        *,
        limit: int = 5,
        source_file: str | None = None,
        min_similarity: float = 0.55,
        retrieve_mode: str = "hybrid",
        expand_parent: bool = False,
        corpus_names: list[str] | None = None,
        categories: list[str] | None = None,
    ) -> list[schemas.DocumentChunkSearchResult]:
        mode = (retrieve_mode or "hybrid").strip().lower()
        if mode not in _RETRIEVE_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"retrieve_mode 仅支持: {', '.join(_RETRIEVE_MODES)}",
            )
        ensure_chunk_table(self.db, BUSINESS_CHUNK_TABLE)
        scope = resolve_corpus_names(
            self.db,
            corpus_name=corpus_name,
            corpus_names=corpus_names,
            categories=normalize_category_list(categories),
        )
        if scope is not None and not scope:
            return []
        if not query or not query.strip():
            return self._list_recent(scope, limit, source_file)

        raw_query = query.strip()
        resolved_lang = detect_lang(raw_query)
        retrieve_query = _rewrite_query(raw_query) if len(raw_query) >= 4 else raw_query
        try:
            items = retrieve(
                self.db,
                retrieve_query,
                table_name=BUSINESS_CHUNK_TABLE,
                corpus_names=scope,
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
        corpus_name: str | None,
        query: str | None,
        *,
        limit: int = 5,
        min_similarity: float = 0.55,
        retrieve_mode: str = "hybrid",
        expand_parent: bool = True,
        source_file: str | None = None,
        corpus_names: list[str] | None = None,
        categories: list[str] | None = None,
    ) -> schemas.DocumentSearchPolishedResult:
        sources = self.search(
            corpus_name,
            query,
            limit=limit,
            min_similarity=min_similarity,
            retrieve_mode=retrieve_mode,
            expand_parent=expand_parent,
            source_file=source_file,
            corpus_names=corpus_names,
            categories=categories,
        )
        if not query or not query.strip():
            original = [
                schemas.DocumentSearchPolishedSource.from_search_hit(
                    i,
                    c,
                    f"{c.source_file} · {c.section_title or c.section_path or '正文'}",
                )
                for i, c in enumerate(sources, start=1)
            ]
            return schemas.DocumentSearchPolishedResult(
                query="",
                polished_answer=f"未提供查询文本，以下为资料库前 {len(sources)} 条切块。",
                source_count=len(original),
                original_sources=original,
            )
        if not sources:
            return schemas.DocumentSearchPolishedResult(
                query=query,
                polished_answer="未检索到相关文档片段，无法生成回答。",
                source_count=0,
                original_sources=[],
            )

        blocks = []
        original = []
        for i, chunk in enumerate(sources, start=1):
            header = chunk.section_title or chunk.section_path or "正文"
            label = f"{chunk.source_file} · {header}"
            blocks.append(f"[片段{i}] 来源: {label}\n{chunk.content}")
            original.append(schemas.DocumentSearchPolishedSource.from_search_hit(i, chunk, label))
        user_prompt = (
            f"用户问题：{query}\n\n共检索到 {len(sources)} 条相关片段，请综合后回答：\n\n"
            + "\n\n".join(blocks)
        )
        answer = chat_completion(
            _SYSTEM_PROMPT,
            user_prompt,
            temperature=0.5,
            disable_thinking=True,
            caller="rag.corpora.search_and_llm",
        )
        return schemas.DocumentSearchPolishedResult(
            query=query, polished_answer=answer, source_count=len(original), original_sources=original
        )
