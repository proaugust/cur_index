from sqlalchemy.orm import Session

from app import models, schemas
from app.crud import modules as crud
from app.services.modules.chunk_lang import DEFAULT_CHUNK_LANG, detect_lang
from app.services.modules.chunk_table_ops import embedding_preview, source_file_like_pattern
from app.services.shared.embedding import embed_query
from app.services.shared.llm import chat_completion

_SYSTEM_PROMPT = (
    "你是专业的文档问答助手。用户会提供一个问题和若干条检索到的文档片段。"
    "你的任务是把**所有相关片段的信息综合起来**，写成一份完整、易读的回答，而不是简单复述某一条片段。\n"
)


class DocumentSearchService:
    def __init__(self, db: Session):
        self.db = db

    def _list_recent_chunks(
        self,
        limit: int = 5,
        source_file: str | None = None,
        lang: str | None = None,
    ) -> list[schemas.DocumentChunkSearchResult]:
        chunks, _ = crud.get_document_chunks(self.db, source_file=source_file, page=1, page_size=max(limit * 3, limit))
        results: list[schemas.DocumentChunkSearchResult] = []
        for chunk in chunks:
            chunk_lang = getattr(chunk, "lang", None) or DEFAULT_CHUNK_LANG
            if lang and chunk_lang != lang:
                continue
            results.append(
                schemas.DocumentChunkSearchResult(
                    id=chunk.id,
                    source_file=chunk.source_file,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    char_count=chunk.char_count,
                    lang=chunk_lang,
                    embedding_preview=embedding_preview(chunk.embedding),
                    similarity=0.0,
                )
            )
            if len(results) >= limit:
                break
        return results

    def search(
        self,
        query: str | None,
        limit: int = 5,
        source_file: str | None = None,
        min_similarity: float = 0.55,
    ) -> list[schemas.DocumentChunkSearchResult]:
        resolved = detect_lang(query) if query and query.strip() else None
        if not query or not query.strip():
            return self._list_recent_chunks(limit=limit, source_file=source_file)

        query_vector = embed_query(query.strip())
        distance_expr = models.DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        q = self.db.query(models.DocumentChunk, distance_expr).filter(models.DocumentChunk.embedding.isnot(None))
        if resolved:
            q = q.filter(models.DocumentChunk.lang == resolved)
        file_pattern = source_file_like_pattern(source_file)
        if file_pattern:
            q = q.filter(models.DocumentChunk.source_file.ilike(file_pattern))
        rows = q.order_by(distance_expr).limit(limit).all()

        results: list[schemas.DocumentChunkSearchResult] = []
        for chunk, distance in rows:
            similarity = round(1 - distance, 4)
            if similarity < min_similarity:
                continue
            results.append(
                schemas.DocumentChunkSearchResult(
                    id=chunk.id,
                    source_file=chunk.source_file,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    char_count=chunk.char_count,
                    lang=getattr(chunk, "lang", None) or DEFAULT_CHUNK_LANG,
                    embedding_preview=embedding_preview(chunk.embedding),
                    similarity=similarity,
                )
            )
        return results

    def search_polished(
        self,
        query: str | None,
        limit: int = 5,
        min_similarity: float = 0.55,
    ) -> schemas.DocumentSearchPolishedResult:
        if not query or not query.strip():
            sources = self._list_recent_chunks(limit=limit)
            original_sources = [
                schemas.DocumentSearchPolishedSource(
                    snippet_index=index,
                    id=chunk.id,
                    source_file=chunk.source_file,
                    source_label=f"{chunk.source_file} · {chunk.section_title or chunk.section_path or '正文'}",
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    char_count=chunk.char_count,
                    similarity=chunk.similarity,
                    embedding_preview=chunk.embedding_preview,
                    lang=chunk.lang,
                )
                for index, chunk in enumerate(sources, start=1)
            ]
            return schemas.DocumentSearchPolishedResult(
                query="",
                polished_answer=f"未提供查询文本，以下为库中前 {len(sources)} 条切块。",
                source_count=len(original_sources),
                original_sources=original_sources,
            )

        sources = self.search(query, limit=limit, min_similarity=min_similarity)
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
                schemas.DocumentSearchPolishedSource(
                    snippet_index=index,
                    id=chunk.id,
                    source_file=chunk.source_file,
                    source_label=source_label,
                    section_title=chunk.section_title,
                    section_path=chunk.section_path,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    char_count=chunk.char_count,
                    similarity=chunk.similarity,
                    embedding_preview=chunk.embedding_preview,
                    lang=chunk.lang,
                )
            )

        user_prompt = f"用户问题：{query}\n\n共检索到 {len(sources)} 条相关片段，请综合后回答：\n\n" + "\n\n".join(context_blocks)
        polished_answer = chat_completion(
            _SYSTEM_PROMPT, user_prompt, temperature=0.5, disable_thinking=True, caller="rag.search_and_llm"
        )

        return schemas.DocumentSearchPolishedResult(
            query=query, polished_answer=polished_answer, source_count=len(original_sources), original_sources=original_sources
        )
