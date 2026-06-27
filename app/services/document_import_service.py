from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.services.embedding import embed_texts
from app.services.text_chunker import CHUNK_LEN, CHUNK_OVERLAP, SMALL_PIECE_LEN, chunk_document, parse_sections


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
    ) -> schemas.DocumentImportResult:
        if min_chunk_len < 5:
            raise HTTPException(status_code=400, detail="min_chunk_len 不能小于 5")
        if max_chunk_len < min_chunk_len:
            raise HTTPException(status_code=400, detail="max_chunk_len 不能小于 min_chunk_len")

        chunks = chunk_document(
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
                    "embedding": vector,
                }
            )

        created = crud.bulk_create_document_chunks(self.db, rows)

        return schemas.DocumentImportResult(source_file=source_file, sections=len(parse_sections(text)), chunks=len(created))

    def import_file(self, file_path: str, replace_existing: bool = True) -> schemas.DocumentImportResult:
        path = Path(file_path)
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"文件不存在: {file_path}")

        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="文件编码必须是 UTF-8") from exc

        return self.import_text(text, str(path.resolve()), replace_existing=replace_existing)
