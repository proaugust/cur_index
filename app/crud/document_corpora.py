"""业务知识库（document_corpora）CRUD：切块一律写入 document_business_chunks。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session, defer

from app import models
from app.services.modules.chunk_table_ops import (
    BUSINESS_CHUNK_TABLE,
    ensure_chunk_table,
    name_to_slug,
    source_file_like_pattern,
)


def _model():
    return models.DocumentBusinessChunk


def list_corpora(db: Session, category: str | None = None) -> list[models.DocumentCorpus]:
    query = db.query(models.DocumentCorpus)
    if category and category.strip():
        query = query.filter(models.DocumentCorpus.category == category.strip())
    return query.order_by(models.DocumentCorpus.id).all()


def get_corpus_by_name(db: Session, name: str) -> models.DocumentCorpus | None:
    return db.query(models.DocumentCorpus).filter(models.DocumentCorpus.name == name.strip()).first()


def get_or_create_corpus(
    db: Session,
    name: str,
    *,
    default_chunk_strategy: str = "structure",
    lang: str = "zh",
    category: str = "other",
) -> models.DocumentCorpus:
    ensure_chunk_table(db, BUSINESS_CHUNK_TABLE)
    existing = get_corpus_by_name(db, name)
    if existing is not None:
        dirty = False
        if existing.table_name != BUSINESS_CHUNK_TABLE:
            existing.table_name = BUSINESS_CHUNK_TABLE
            dirty = True
        if lang and existing.lang != lang:
            existing.lang = lang
            dirty = True
        if category and getattr(existing, "category", None) != category:
            existing.category = category
            dirty = True
        if dirty:
            db.commit()
            db.refresh(existing)
        return existing

    base_slug = name_to_slug(name)
    slug = base_slug
    suffix = 2
    while db.query(models.DocumentCorpus).filter(models.DocumentCorpus.table_slug == slug).first():
        slug = f"{base_slug}_{suffix}"[:48]
        suffix += 1

    corpus = models.DocumentCorpus(
        name=name.strip(),
        table_slug=slug,
        table_name=BUSINESS_CHUNK_TABLE,
        default_chunk_strategy=default_chunk_strategy,
        category=category or "other",
        lang=lang,
    )
    db.add(corpus)
    db.commit()
    db.refresh(corpus)
    return corpus


def delete_chunks_by_source(
    db: Session, corpus_name: str, source_file: str, *, commit: bool = True
) -> int:
    model = _model()
    deleted = (
        db.query(model)
        .filter(model.corpus_name == corpus_name, model.source_file == source_file)
        .delete(synchronize_session=False)
    )
    if commit:
        db.commit()
    return deleted


def delete_chunks_by_sources(
    db: Session, corpus_name: str, source_files: list[str], *, commit: bool = True
) -> int:
    if not source_files:
        return 0
    model = _model()
    deleted = (
        db.query(model)
        .filter(model.corpus_name == corpus_name, model.source_file.in_(source_files))
        .delete(synchronize_session=False)
    )
    if commit:
        db.commit()
    return deleted


def clear_all_chunks(db: Session, corpus_name: str) -> int:
    """清空指定资料名下的切块，保留注册与共享物理表。"""
    model = _model()
    deleted = db.query(model).filter(model.corpus_name == corpus_name).delete(synchronize_session=False)
    db.commit()
    return deleted


def bulk_insert_chunks(
    db: Session, rows: list[dict], *, commit: bool = True
) -> int:
    model = _model()
    items = [model(**row) for row in rows]
    db.add_all(items)
    if commit:
        db.commit()
    return len(items)


def list_source_files(db: Session, corpus_name: str | None = None) -> list[tuple[str, str]]:
    model = _model()
    query = db.query(model.corpus_name, model.source_file).distinct()
    if corpus_name:
        query = query.filter(model.corpus_name == corpus_name)
    rows = query.order_by(model.corpus_name, model.source_file).all()
    return [(row[0], row[1]) for row in rows]


def list_source_files_page(
    db: Session,
    corpus_name: str | None = None,
    source_file: str | None = None,
    *,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[tuple[str, str]], int]:
    model = _model()
    query = db.query(model.corpus_name, model.source_file).distinct()
    if corpus_name:
        query = query.filter(model.corpus_name == corpus_name)
    file_pattern = source_file_like_pattern(source_file)
    if file_pattern:
        query = query.filter(model.source_file.ilike(file_pattern))
    query = query.order_by(model.corpus_name, model.source_file)
    total = int(query.count())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return [(row[0], row[1]) for row in rows], total


def list_chunks(
    db: Session,
    corpus_name: str | None = None,
    source_file: str | None = None,
    *,
    corpus_names: list[str] | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list, int]:
    model = _model()
    query = db.query(model).options(defer(model.embedding, raiseload=True))
    names = [n for n in (corpus_names or []) if n] if corpus_names is not None else None
    if names is not None:
        if len(names) == 1:
            query = query.filter(model.corpus_name == names[0])
        elif names:
            query = query.filter(model.corpus_name.in_(names))
        else:
            return [], 0
    elif corpus_name:
        query = query.filter(model.corpus_name == corpus_name)
    file_pattern = source_file_like_pattern(source_file)
    if file_pattern:
        query = query.filter(model.source_file.ilike(file_pattern))
    query = query.order_by(model.id)
    total = int(query.count())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def count_chunks(db: Session, corpus_name: str) -> int:
    model = _model()
    return int(db.query(func.count(model.id)).filter(model.corpus_name == corpus_name).scalar() or 0)


def get_chunk_by_id(db: Session, corpus_name: str, chunk_id: int):
    model = _model()
    return (
        db.query(model)
        .filter(model.corpus_name == corpus_name, model.id == chunk_id)
        .first()
    )


def get_next_chunk_index(db: Session, corpus_name: str, source_file: str) -> int:
    model = _model()
    max_index = (
        db.query(func.max(model.chunk_index))
        .filter(model.corpus_name == corpus_name, model.source_file == source_file)
        .scalar()
    )
    return (max_index or -1) + 1


def create_chunk(
    db: Session,
    corpus_name: str,
    *,
    source_file: str,
    content: str,
    section_title: str = "",
    section_path: str = "",
    chunk_index: int | None = None,
    embedding: list[float] | None = None,
    lang: str = "zh",
):
    model = _model()
    if chunk_index is None:
        chunk_index = get_next_chunk_index(db, corpus_name, source_file)
    row = model(
        corpus_name=corpus_name,
        source_file=source_file,
        section_title=section_title,
        section_path=section_path,
        chunk_index=chunk_index,
        content=content,
        char_count=len(content),
        lang=lang,
        embedding=embedding,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_chunk(
    db: Session,
    row,
    *,
    content: str | None = None,
    section_title: str | None = None,
    section_path: str | None = None,
    char_count: int | None = None,
    embedding: list[float] | None = None,
    lang: str | None = None,
):
    if content is not None:
        row.content = content
    if section_title is not None:
        row.section_title = section_title
    if section_path is not None:
        row.section_path = section_path
    if char_count is not None:
        row.char_count = char_count
    if embedding is not None:
        row.embedding = embedding
    if lang is not None:
        row.lang = lang
    db.commit()
    db.refresh(row)
    return row


def delete_chunk_by_id(db: Session, corpus_name: str, chunk_id: int) -> bool:
    model = _model()
    deleted = (
        db.query(model)
        .filter(model.corpus_name == corpus_name, model.id == chunk_id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted > 0


def delete_corpus(db: Session, corpus: models.DocumentCorpus) -> tuple[str, int]:
    """删注册行并清空该资料名切块（不 DROP 共享表）。返回 (table_name, 删除切块数)。"""
    model = _model()
    n = (
        db.query(model)
        .filter(model.corpus_name == corpus.name)
        .delete(synchronize_session=False)
    )
    db.delete(corpus)
    db.commit()
    return BUSINESS_CHUNK_TABLE, int(n)
