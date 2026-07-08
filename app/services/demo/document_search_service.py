from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.shared.embedding import embed_query
from app.services.shared.llm import chat_completion

_SYSTEM_PROMPT = (
    "你是专业的文档问答助手。用户会提供一个问题和若干条检索到的文档片段。"
    "你的任务是把**所有相关片段的信息综合起来**，写成一份完整、易读的回答，而不是简单复述某一条片段。\n"
    # "要求：\n"
    # "1. 先用 1～2 句话给出直接结论（回答用户问题）；\n"
    # "2. 再用分点列表展开细节，合并多条片段中的信息，去重并理顺逻辑；\n"
    # "3. 重要事实后标注来源，格式为〔片段N〕，N 对应用户提供的片段编号；\n"
    # "4. 仅使用片段中已有的信息，不要编造；片段之间有矛盾时如实指出；\n"
    # "5. 若片段不足以完整回答，先写已知部分，最后说明还缺少什么信息。\n"
    # "使用 Markdown 格式输出（可用 **加粗**、列表等），让回答看起来充实、有条理。"
    # "You are an AI assistant. Answer based on the provided context. Answer based on the provided context only,"
    # " do not use other informations. If you cannot answer, say 'I need more context.'",
)


class DocumentSearchService:
    def __init__(self, db: Session):
        self.db = db

    def _list_recent_chunks(
        self, limit: int = 5, source_file: str | None = None
    ) -> list[schemas.DocumentChunkSearchResult]:
        chunks = crud.get_document_chunks(self.db, source_file=source_file, limit=limit)
        return [
            schemas.DocumentChunkSearchResult(
                id=chunk.id,
                source_file=chunk.source_file,
                section_title=chunk.section_title,
                section_path=chunk.section_path,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                char_count=chunk.char_count,
                similarity=0.0,
            )
            for chunk in chunks
        ]

    def search(
        self, query: str | None, limit: int = 5, source_file: str | None = None, min_similarity: float = 0.55
    ) -> list[schemas.DocumentChunkSearchResult]:
        if not query or not query.strip():
            return self._list_recent_chunks(limit=limit, source_file=source_file)

        query_vector = embed_query(query.strip())
        distance_expr = models.DocumentChunk.embedding.cosine_distance(query_vector).label("distance")
        q = self.db.query(models.DocumentChunk, distance_expr).filter(models.DocumentChunk.embedding.isnot(None))
        if source_file:
            q = q.filter(models.DocumentChunk.source_file == source_file)
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
                    similarity=similarity,
                )
            )
        return results

    def search_polished(
        self, query: str | None, limit: int = 5, min_similarity: float = 0.55
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
                )
            )

        user_prompt = f"用户问题：{query}\n\n共检索到 {len(sources)} 条相关片段，请综合后回答：\n\n" + "\n\n".join(context_blocks)
        polished_answer = chat_completion(_SYSTEM_PROMPT, user_prompt, temperature=0.5, caller="rag.search_and_llm")

        return schemas.DocumentSearchPolishedResult(
            query=query, polished_answer=polished_answer, source_count=len(original_sources), original_sources=original_sources
        )
