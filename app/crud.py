from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas


def get_items(db: Session) -> list[models.Item]:
    return db.query(models.Item).all()


def create_item(db: Session, item: schemas.ItemCreate) -> models.Item:
    db_item = models.Item(title=item.title)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_document_chunks_by_source(db: Session, source_file: str) -> int:
    deleted = (
        db.query(models.DocumentChunk)
        .filter(models.DocumentChunk.source_file == source_file)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted


def bulk_create_document_chunks(
    db: Session,
    rows: list[dict],
) -> list[models.DocumentChunk]:
    items = [models.DocumentChunk(**row) for row in rows]
    db.add_all(items)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


def get_distinct_source_files(db: Session) -> list[str]:
    rows = (
        db.query(models.DocumentChunk.source_file)
        .distinct()
        .order_by(models.DocumentChunk.source_file)
        .all()
    )
    return [row[0] for row in rows]


def get_document_chunks(
    db: Session,
    source_file: str | None = None,
    limit: int = 20,
) -> list[models.DocumentChunk]:
    query = db.query(models.DocumentChunk)
    if source_file:
        query = query.filter(models.DocumentChunk.source_file == source_file)
    return query.order_by(models.DocumentChunk.id).limit(limit).all()


def clear_complaint_categories(db: Session) -> None:
    db.query(models.ComplaintCategory).delete(synchronize_session=False)
    db.commit()


def clear_complaints(db: Session) -> None:
    db.query(models.Complaint).delete(synchronize_session=False)
    db.commit()


def get_complaint_categories(db: Session) -> list[models.ComplaintCategory]:
    return db.query(models.ComplaintCategory).order_by(models.ComplaintCategory.id).all()


def get_unclassified_complaints(db: Session) -> list[models.Complaint]:
    return db.query(models.Complaint).filter(models.Complaint.category_id.is_(None)).all()


def count_complaints(db: Session) -> int:
    return db.query(models.Complaint).count()


def count_classified_complaints(db: Session) -> int:
    return db.query(models.Complaint).filter(models.Complaint.category_id.isnot(None)).count()


class _ComplaintStatRow:
    def __init__(self, category_id: int, category_name: str, count: int):
        self.category_id = category_id
        self.category_name = category_name
        self.count = count


def get_complaint_stats(db: Session) -> list[_ComplaintStatRow]:
    rows = (
        db.query(
            models.ComplaintCategory.id,
            models.ComplaintCategory.name,
            func.count(models.Complaint.id),
        )
        .join(models.Complaint, models.Complaint.category_id == models.ComplaintCategory.id)
        .group_by(models.ComplaintCategory.id, models.ComplaintCategory.name)
        .order_by(func.count(models.Complaint.id).desc())
        .all()
    )
    return [
        _ComplaintStatRow(category_id=row[0], category_name=row[1], count=row[2])
        for row in rows
    ]


def get_complaint_samples(
    db: Session,
    category_name: str | None = None,
    limit: int = 10,
) -> list[models.Complaint]:
    query = db.query(models.Complaint).join(
        models.ComplaintCategory,
        models.Complaint.category_id == models.ComplaintCategory.id,
        isouter=True,
    )
    if category_name:
        query = query.filter(models.ComplaintCategory.name == category_name)
    return query.order_by(models.Complaint.id).limit(limit).all()
