"""业务知识库（document_corpora）CRUD 与切块表读写。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.services.modules.chunk_table_ops import (
    ensure_chunk_table,
    get_chunk_model,
    name_to_slug,
    table_name_for_slug,
)


def list_corpora(db: Session) -> list[models.DocumentCorpus]:
    return db.query(models.DocumentCorpus).order_by(models.DocumentCorpus.id).all()


def get_corpus_by_name(db: Session, name: str) -> models.DocumentCorpus | None:
    return db.query(models.DocumentCorpus).filter(models.DocumentCorpus.name == name.strip()).first()


def get_or_create_corpus(
    db: Session,
    name: str,
    *,
    default_chunk_strategy: str = "structure",
) -> models.DocumentCorpus:
    existing = get_corpus_by_name(db, name)
    if existing is not None:
        ensure_chunk_table(db, existing.table_name)
        return existing

    base_slug = name_to_slug(name)
    slug = base_slug
    suffix = 2
    while db.query(models.DocumentCorpus).filter(models.DocumentCorpus.table_slug == slug).first():
        slug = f"{base_slug}_{suffix}"[:48]
        suffix += 1

    table_name = table_name_for_slug(slug)
    ensure_chunk_table(db, table_name)
    corpus = models.DocumentCorpus(
        name=name.strip(),
        table_slug=slug,
        table_name=table_name,
        default_chunk_strategy=default_chunk_strategy,
    )
    db.add(corpus)
    db.commit()
    db.refresh(corpus)
    return corpus


def delete_chunks_by_source(
    db: Session, table_name: str, source_file: str, *, commit: bool = True
) -> int:
    model = get_chunk_model(table_name)
    deleted = db.query(model).filter(model.source_file == source_file).delete(synchronize_session=False)
    if commit:
        db.commit()
    return deleted


def delete_chunks_by_sources(
    db: Session, table_name: str, source_files: list[str], *, commit: bool = True
) -> int:
    if not source_files:
        return 0
    model = get_chunk_model(table_name)
    deleted = (
        db.query(model)
        .filter(model.source_file.in_(source_files))
        .delete(synchronize_session=False)
    )
    if commit:
        db.commit()
    return deleted


def clear_all_chunks(db: Session, table_name: str) -> int:
    """清空切块表全部行，保留表结构与 document_corpora 注册。"""
    model = get_chunk_model(table_name)
    deleted = db.query(model).delete(synchronize_session=False)
    db.commit()
    return deleted


def bulk_insert_chunks(
    db: Session, table_name: str, rows: list[dict], *, commit: bool = True
) -> int:
    model = get_chunk_model(table_name)
    items = [model(**row) for row in rows]
    db.add_all(items)
    if commit:
        db.commit()
    return len(items)


def list_source_files(db: Session, table_name: str) -> list[str]:
    model = get_chunk_model(table_name)
    rows = db.query(model.source_file).distinct().order_by(model.source_file).all()
    return [row[0] for row in rows]


def list_chunks(db: Session, table_name: str, source_file: str | None = None, limit: int = 20) -> list:
    model = get_chunk_model(table_name)
    query = db.query(model)
    if source_file:
        query = query.filter(model.source_file == source_file)
    return query.order_by(model.id).limit(limit).all()


def count_chunks(db: Session, table_name: str) -> int:
    model = get_chunk_model(table_name)
    return int(db.query(func.count(model.id)).scalar() or 0)
