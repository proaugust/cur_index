"""业务知识库向量检索（按资料名路由到物理切块表）。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import document_corpora as corpus_crud
from app.services.modules.chunk_table_ops import row_to_dict
from app.services.modules.corpus_retrieve import retrieve
from app.services.shared.llm import chat_completion

_SYSTEM_PROMPT = (
    "你是专业的文档问答助手。用户会提供一个问题和若干条检索到的文档片段。"
    "你的任务是把**所有相关片段的信息综合起来**，写成一份完整、易读的回答，而不是简单复述某一条片段。\n"
)
_RETRIEVE_MODES = ("vector", "hybrid", "hybrid_rerank")


class CorpusSearchService:
    def __init__(self, db: Session):
        self.db = db

    def _require_corpus(self, corpus_name: str):
        from app.services.modules.chunk_table_ops import ensure_chunk_table

        corpus = corpus_crud.get_corpus_by_name(self.db, corpus_name)
        if corpus is None:
            raise HTTPException(status_code=404, detail=f"资料库不存在: {corpus_name}")
        ensure_chunk_table(self.db, corpus.table_name)
        return corpus

    def list_files(self, corpus_name: str) -> schemas.CorpusFileListResult:
        corpus = self._require_corpus(corpus_name)
        files = [
            schemas.CorpusFileItem(source_file=name)
            for name in corpus_crud.list_source_files(self.db, corpus.table_name)
        ]
        return schemas.CorpusFileListResult(corpus_name=corpus.name, table_name=corpus.table_name, files=files)

    def _list_recent(self, table_name: str, limit: int, source_file: str | None):
        rows = corpus_crud.list_chunks(self.db, table_name, source_file=source_file, limit=limit)
        return [schemas.DocumentChunkSearchResult(**row_to_dict(row), similarity=0.0) for row in rows]

    def search(
        self,
        corpus_name: str,
        query: str | None,
        *,
        limit: int = 5,
        source_file: str | None = None,
        min_similarity: float = 0.55,
        retrieve_mode: str = "hybrid",
        expand_parent: bool = False,
    ) -> list[schemas.DocumentChunkSearchResult]:
        mode = (retrieve_mode or "hybrid").strip().lower()
        if mode not in _RETRIEVE_MODES:
            raise HTTPException(
                status_code=400,
                detail=f"retrieve_mode 仅支持: {', '.join(_RETRIEVE_MODES)}",
            )
        corpus = self._require_corpus(corpus_name)
        if not query or not query.strip():
            return self._list_recent(corpus.table_name, limit, source_file)

        try:
            items = retrieve(
                self.db,
                corpus.table_name,
                query.strip(),
                limit=limit,
                min_similarity=min_similarity,
                source_file=source_file,
                retrieve_mode=mode,
                expand_parent=expand_parent,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [schemas.DocumentChunkSearchResult(**item) for item in items]

    def search_polished(
        self,
        corpus_name: str,
        query: str | None,
        *,
        limit: int = 5,
        min_similarity: float = 0.55,
        retrieve_mode: str = "hybrid",
        expand_parent: bool = True,
    ) -> schemas.DocumentSearchPolishedResult:
        sources = self.search(
            corpus_name,
            query,
            limit=limit,
            min_similarity=min_similarity,
            retrieve_mode=retrieve_mode,
            expand_parent=expand_parent,
        )
        if not query or not query.strip():
            original = [
                schemas.DocumentSearchPolishedSource(
                    snippet_index=i,
                    id=c.id,
                    source_file=c.source_file,
                    source_label=f"{c.source_file} · {c.section_title or c.section_path or '正文'}",
                    section_title=c.section_title,
                    section_path=c.section_path,
                    chunk_index=c.chunk_index,
                    content=c.content,
                    char_count=c.char_count,
                    similarity=c.similarity,
                    embedding_preview=c.embedding_preview,
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
                query=query, polished_answer="未检索到相关文档片段，无法生成回答。", source_count=0, original_sources=[]
            )

        blocks = []
        original = []
        for i, chunk in enumerate(sources, start=1):
            header = chunk.section_title or chunk.section_path or "正文"
            label = f"{chunk.source_file} · {header}"
            blocks.append(f"[片段{i}] 来源: {label}\n{chunk.content}")
            original.append(
                schemas.DocumentSearchPolishedSource(
                    snippet_index=i,
                    id=chunk.id,
                    source_file=chunk.source_file,
                    source_label=label,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    char_count=chunk.char_count,
                    similarity=chunk.similarity,
                    embedding_preview=chunk.embedding_preview,
                )
            )
        user_prompt = f"用户问题：{query}\n\n共检索到 {len(sources)} 条相关片段，请综合后回答：\n\n" + "\n\n".join(blocks)
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
