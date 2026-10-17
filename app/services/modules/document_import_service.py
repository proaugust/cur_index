from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.crud import modules as crud
from app.services.modules.chunk_lang import detect_lang
from app.services.modules.chunk_table_ops import GENERAL_CHUNK_TABLE, refresh_search_vectors
from app.services.shared.embedding import embed_texts
from app.services.shared.structure_chunker import (
    MD_HEADING,
    chunk_document_structure,
    chunk_section_structure,
    parse_markdown_sections,
)
from app.services.shared.text_chunker import (
    CHUNK_LEN,
    CHUNK_OVERLAP,
    SECTION_SEP,
    SMALL_PIECE_LEN,
    TITLE_PATTERN,
    TextSection,
    parse_sections_kept,
)


class DocumentImportService:
    def __init__(self, db: Session):
        self.db = db

    def import_text(
        self,
        text: str,
        source_file: str,
        replace_existing: bool = True,
        min_chunk_len: int = SMALL_PIECE_LEN,
        max_chunk_len: int = CHUNK_LEN,
        chunk_overlap: int = CHUNK_OVERLAP,
        original_import_path: str | None = None,
    ) -> schemas.DocumentImportResult:
        if min_chunk_len < 5:
            raise HTTPException(status_code=400, detail="min_chunk_len 不能小于 5")
        if max_chunk_len < min_chunk_len:
            raise HTTPException(status_code=400, detail="max_chunk_len 不能小于 min_chunk_len")
        resolved_lang = detect_lang(text)

        chunks, section_count = self._chunk_text(
            text,
            min_chunk_len=min_chunk_len,
            max_chunk_len=max_chunk_len,
            chunk_overlap=chunk_overlap,
        )
        if not chunks:
            raise HTTPException(status_code=400, detail="未解析到有效文本块")

        if replace_existing:
            crud.delete_document_chunks_by_source(self.db, source_file)

        vectors = embed_texts([chunk.content for chunk in chunks])
        rows = []
        for chunk, vector in zip(chunks, vectors):
            rows.append(
                {
                    "source_file": source_file,
                    "section_title": chunk.section_title,
                    "section_path": chunk.section_path,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "char_count": len(chunk.content),
                    "lang": resolved_lang,
                    "original_import_path": original_import_path,
                    "embedding": vector,
                }
            )

        created = crud.bulk_create_document_chunks(self.db, rows)
        refresh_search_vectors(self.db, GENERAL_CHUNK_TABLE, source_files=[source_file])
        self.db.commit()
        return schemas.DocumentImportResult(source_file=source_file, sections=section_count, chunks=len(created))

    def _chunk_text(
        self,
        text: str,
        *,
        min_chunk_len: int,
        max_chunk_len: int,
        chunk_overlap: int,
    ):
        """【标题】/==== 按节保留换行后做段落切块；Markdown 标题走结构切块。"""
        marked = SECTION_SEP.search(text) or any(
            TITLE_PATTERN.match(line.strip()) for line in text.splitlines()
        )
        if marked:
            sections = parse_sections_kept(text)
            chunks = []
            for section in sections:
                chunks.extend(
                    chunk_section_structure(
                        section,
                        min_chunk_len=min_chunk_len,
                        max_chunk_len=max_chunk_len,
                        chunk_overlap=chunk_overlap,
                    )
                )
            return chunks, len(sections)
        if any(MD_HEADING.match(line.strip()) for line in text.splitlines()):
            return chunk_document_structure(
                text,
                min_chunk_len=min_chunk_len,
                max_chunk_len=max_chunk_len,
                chunk_overlap=chunk_overlap,
            ), len(parse_markdown_sections(text))
        section = TextSection(title="", path="", content=text)
        chunks = chunk_section_structure(
            section,
            min_chunk_len=min_chunk_len,
            max_chunk_len=max_chunk_len,
            chunk_overlap=chunk_overlap,
        )
        return chunks, 1 if chunks else 0

    def import_file(self, file_path: str, replace_existing: bool = True) -> schemas.DocumentImportResult:
        path = Path(file_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"文件不存在: {file_path}")

        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="文件编码必须是 UTF-8") from exc

        return self.import_text(text, str(path.resolve()), replace_existing=replace_existing,
                                original_import_path=str(path.resolve()))
