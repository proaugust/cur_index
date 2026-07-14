"""业务知识库导入：资料名 → 物理表，支持单文件 / 本机文件夹。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import document_corpora as corpus_crud
from app.services.modules.chunk_table_ops import (
    HNSW_BULK_THRESHOLD,
    create_hnsw_index,
    drop_hnsw_index,
    refresh_search_vectors,
)
from app.services.modules.corpus_retrieve import chunk_embed_text
from app.services.shared.embedding import embed_texts
from app.services.shared.structure_chunker import (
    DEFAULT_MAX_CHUNK,
    DEFAULT_MIN_CHUNK,
    DEFAULT_OVERLAP,
    chunk_document_structure,
    parse_markdown_sections,
)
from app.services.shared.text_chunker import chunk_document, parse_sections

_TEXT_SUFFIXES = {".md", ".markdown", ".txt"}
ProgressCb = Callable[[int, int], None]


class CorpusImportService:
    def __init__(self, db: Session):
        self.db = db

    def _chunk_text(
        self,
        text: str,
        *,
        strategy: str,
        min_chunk_len: int,
        max_chunk_len: int,
        chunk_overlap: int,
    ):
        if strategy == "legacy":
            return chunk_document(
                text,
                min_chunk_len=min_chunk_len,
                max_chunk_len=max_chunk_len,
                chunk_overlap=chunk_overlap,
            ), len(parse_sections(text))
        return chunk_document_structure(
            text,
            min_chunk_len=min_chunk_len,
            max_chunk_len=max_chunk_len,
            chunk_overlap=chunk_overlap,
        ), len(parse_markdown_sections(text))

    def _validate_import(self, corpus_name: str, chunk_strategy: str, min_chunk_len: int, max_chunk_len: int) -> None:
        if not corpus_name.strip():
            raise HTTPException(status_code=400, detail="资料名不能为空")
        if max_chunk_len < min_chunk_len:
            raise HTTPException(status_code=400, detail="max_chunk_len 不能小于 min_chunk_len")
        if chunk_strategy not in ("structure", "legacy"):
            raise HTTPException(status_code=400, detail="chunk_strategy 仅支持 structure / legacy")

    def _persist_rows(
        self,
        table_name: str,
        rows: list[dict],
        *,
        replace_sources: list[str] | None,
    ) -> int:
        if replace_sources:
            corpus_crud.delete_chunks_by_sources(self.db, table_name, replace_sources, commit=False)
        large = len(rows) >= HNSW_BULK_THRESHOLD
        if large:
            drop_hnsw_index(self.db, table_name)
        created = corpus_crud.bulk_insert_chunks(self.db, table_name, rows, commit=False)
        if large:
            create_hnsw_index(self.db, table_name)
        refresh_search_vectors(self.db, table_name, source_files=replace_sources)
        self.db.commit()
        return created

    def _embed_and_persist(
        self,
        corpus,
        prepared: list[tuple[str, int, list]],
        *,
        replace_existing: bool,
    ) -> schemas.CorpusImportResult:
        contents = [
            chunk_embed_text(
                section_path=c.section_path,
                section_title=c.section_title,
                content=c.content,
            )
            for _, _, chunks in prepared
            for c in chunks
        ]
        vectors = embed_texts(contents, show_progress=len(contents) > 32)
        rows: list[dict] = []
        details: list[schemas.DocumentImportResult] = []
        idx = 0
        for source_file, section_count, chunks in prepared:
            for chunk in chunks:
                rows.append(
                    {
                        "source_file": source_file,
                        "section_title": chunk.section_title,
                        "section_path": chunk.section_path,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "char_count": len(chunk.content),
                        "embedding": vectors[idx],
                    }
                )
                idx += 1
            details.append(
                schemas.DocumentImportResult(
                    source_file=source_file, sections=section_count, chunks=len(chunks)
                )
            )
        sources = [s for s, _, _ in prepared] if replace_existing else None
        created = self._persist_rows(corpus.table_name, rows, replace_sources=sources)
        return schemas.CorpusImportResult(
            corpus_name=corpus.name,
            table_name=corpus.table_name,
            files=len(details),
            chunks=created,
            details=details,
        )

    def import_text(
        self,
        text: str,
        *,
        corpus_name: str,
        source_file: str,
        replace_existing: bool = True,
        chunk_strategy: str = "structure",
        min_chunk_len: int = DEFAULT_MIN_CHUNK,
        max_chunk_len: int = DEFAULT_MAX_CHUNK,
        chunk_overlap: int = DEFAULT_OVERLAP,
    ) -> schemas.DocumentImportResult:
        self._validate_import(corpus_name, chunk_strategy, min_chunk_len, max_chunk_len)
        corpus = corpus_crud.get_or_create_corpus(
            self.db, corpus_name.strip(), default_chunk_strategy=chunk_strategy
        )
        chunks, section_count = self._chunk_text(
            text,
            strategy=chunk_strategy,
            min_chunk_len=min_chunk_len,
            max_chunk_len=max_chunk_len,
            chunk_overlap=chunk_overlap,
        )
        if not chunks:
            raise HTTPException(status_code=400, detail=f"未解析到有效文本块: {source_file}")
        result = self._embed_and_persist(
            corpus,
            [(source_file, section_count, chunks)],
            replace_existing=replace_existing,
        )
        return result.details[0]

    def import_folder(
        self,
        folder_path: str,
        *,
        corpus_name: str,
        replace_existing: bool = True,
        chunk_strategy: str = "structure",
        min_chunk_len: int = DEFAULT_MIN_CHUNK,
        max_chunk_len: int = DEFAULT_MAX_CHUNK,
        chunk_overlap: int = DEFAULT_OVERLAP,
        on_progress: ProgressCb | None = None,
    ) -> schemas.CorpusImportResult:
        self._validate_import(corpus_name, chunk_strategy, min_chunk_len, max_chunk_len)
        root = Path(folder_path)
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"文件夹不存在: {folder_path}")

        files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in _TEXT_SUFFIXES)
        if not files:
            raise HTTPException(status_code=400, detail="文件夹内没有 .md / .txt 文件")

        corpus = corpus_crud.get_or_create_corpus(
            self.db, corpus_name.strip(), default_chunk_strategy=chunk_strategy
        )
        prepared: list[tuple[str, int, list]] = []
        total = len(files)
        for i, path in enumerate(files, start=1):
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"文件编码必须是 UTF-8: {path}") from exc
            chunks, section_count = self._chunk_text(
                text,
                strategy=chunk_strategy,
                min_chunk_len=min_chunk_len,
                max_chunk_len=max_chunk_len,
                chunk_overlap=chunk_overlap,
            )
            if not chunks:
                raise HTTPException(status_code=400, detail=f"未解析到有效文本块: {path}")
            prepared.append((str(path.resolve()), section_count, chunks))
            if on_progress:
                on_progress(i, total)

        return self._embed_and_persist(corpus, prepared, replace_existing=replace_existing)

    def import_upload_or_folder(
        self,
        *,
        corpus_name: str,
        file_name: str | None,
        file_text: str | None,
        folder_path: str | None,
        replace_existing: bool,
        chunk_strategy: str,
        min_chunk_len: int,
        max_chunk_len: int,
        chunk_overlap: int,
        on_progress: ProgressCb | None = None,
    ) -> schemas.CorpusImportResult:
        if folder_path and folder_path.strip():
            return self.import_folder(
                folder_path.strip(),
                corpus_name=corpus_name,
                replace_existing=replace_existing,
                chunk_strategy=chunk_strategy,
                min_chunk_len=min_chunk_len,
                max_chunk_len=max_chunk_len,
                chunk_overlap=chunk_overlap,
                on_progress=on_progress,
            )
        if file_text is None or not file_name:
            raise HTTPException(status_code=400, detail="请上传文件，或填写本机 folder_path")
        one = self.import_text(
            file_text,
            corpus_name=corpus_name,
            source_file=file_name,
            replace_existing=replace_existing,
            chunk_strategy=chunk_strategy,
            min_chunk_len=min_chunk_len,
            max_chunk_len=max_chunk_len,
            chunk_overlap=chunk_overlap,
        )
        if on_progress:
            on_progress(1, 1)
        corpus = corpus_crud.get_corpus_by_name(self.db, corpus_name.strip())
        assert corpus is not None
        return schemas.CorpusImportResult(
            corpus_name=corpus.name,
            table_name=corpus.table_name,
            files=1,
            chunks=one.chunks,
            details=[one],
        )
