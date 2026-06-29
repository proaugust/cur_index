from datetime import date, datetime, time, timedelta

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
    deleted = db.query(models.DocumentChunk).filter(models.DocumentChunk.source_file == source_file).delete(synchronize_session=False)
    db.commit()
    return deleted


def bulk_create_document_chunks(db: Session, rows: list[dict]) -> list[models.DocumentChunk]:
    items = [models.DocumentChunk(**row) for row in rows]
    db.add_all(items)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


def get_distinct_source_files(db: Session) -> list[str]:
    rows = db.query(models.DocumentChunk.source_file).distinct().order_by(models.DocumentChunk.source_file).all()
    return [row[0] for row in rows]


def get_document_chunks(db: Session, source_file: str | None = None, limit: int = 20) -> list[models.DocumentChunk]:
    query = db.query(models.DocumentChunk)
    if source_file:
        query = query.filter(models.DocumentChunk.source_file == source_file)
    return query.order_by(models.DocumentChunk.id).limit(limit).all()


def get_document_chunk_by_id(db: Session, chunk_id: int) -> models.DocumentChunk | None:
    return db.query(models.DocumentChunk).filter(models.DocumentChunk.id == chunk_id).first()


def get_next_chunk_index(db: Session, source_file: str) -> int:
    max_index = db.query(func.max(models.DocumentChunk.chunk_index)).filter(models.DocumentChunk.source_file == source_file).scalar()
    return (max_index or -1) + 1


def create_document_chunk(
    db: Session,
    *,
    source_file: str,
    content: str,
    section_title: str = "",
    section_path: str = "",
    chunk_index: int | None = None,
    embedding: list[float] | None = None,
) -> models.DocumentChunk:
    if chunk_index is None:
        chunk_index = get_next_chunk_index(db, source_file)
    chunk = models.DocumentChunk(
        source_file=source_file,
        section_title=section_title,
        section_path=section_path,
        chunk_index=chunk_index,
        content=content,
        char_count=len(content),
        embedding=embedding,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def update_document_chunk(
    db: Session,
    chunk: models.DocumentChunk,
    *,
    content: str | None = None,
    section_title: str | None = None,
    section_path: str | None = None,
    char_count: int | None = None,
    embedding: list[float] | None = None,
) -> models.DocumentChunk:
    if content is not None:
        chunk.content = content
    if section_title is not None:
        chunk.section_title = section_title
    if section_path is not None:
        chunk.section_path = section_path
    if char_count is not None:
        chunk.char_count = char_count
    if embedding is not None:
        chunk.embedding = embedding
    db.commit()
    db.refresh(chunk)
    return chunk


def delete_document_chunk_by_id(db: Session, chunk_id: int) -> bool:
    deleted = db.query(models.DocumentChunk).filter(models.DocumentChunk.id == chunk_id).delete(synchronize_session=False)
    db.commit()
    return deleted > 0


def clear_complaint_categories(db: Session) -> None:
    db.query(models.ComplaintCategory).delete(synchronize_session=False)
    db.commit()


def clear_complaints(db: Session) -> None:
    db.query(models.Complaint).delete(synchronize_session=False)
    db.commit()


def get_complaint_categories(db: Session) -> list[models.ComplaintCategory]:
    return db.query(models.ComplaintCategory).order_by(models.ComplaintCategory.id).all()


def get_complaint_category_by_name(db: Session, name: str) -> models.ComplaintCategory | None:
    return db.query(models.ComplaintCategory).filter(models.ComplaintCategory.name == name).first()


def list_complaint_categories(db: Session, *, name: str | None = None) -> list[tuple[models.ComplaintCategory, int]]:
    query = (
        db.query(models.ComplaintCategory, func.count(models.Complaint.id))
        .outerjoin(models.Complaint, models.Complaint.category_id == models.ComplaintCategory.id)
        .group_by(models.ComplaintCategory.id)
        .order_by(models.ComplaintCategory.id)
    )
    if name:
        query = query.filter(models.ComplaintCategory.name.ilike(f"%{name}%"))
    return query.all()


def create_complaint_category(
    db: Session,
    *,
    name: str,
    description: str,
    seed_phrases: str,
    embedding: list[float],
) -> models.ComplaintCategory:
    category = models.ComplaintCategory(
        name=name,
        description=description,
        seed_phrases=seed_phrases,
        embedding=embedding,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def create_complaint(
    db: Session,
    *,
    complaint_text: str,
    address: str | None,
    complaint_time: datetime | None,
    embedding: list[float],
    category_id: int | None,
    similarity: float | None,
) -> models.Complaint:
    complaint = models.Complaint(
        complaint_text=complaint_text,
        address=address,
        complaint_time=complaint_time,
        embedding=embedding,
        category_id=category_id,
        similarity=similarity,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


def get_unclassified_complaints(db: Session) -> list[models.Complaint]:
    return db.query(models.Complaint).filter(models.Complaint.category_id.is_(None)).all()


def get_complaints_without_embedding(db: Session) -> list[models.Complaint]:
    return db.query(models.Complaint).filter(models.Complaint.embedding.is_(None)).order_by(models.Complaint.id).all()


def count_complaints(db: Session) -> int:
    return db.query(models.Complaint).count()


def count_classified_complaints(db: Session) -> int:
    return db.query(models.Complaint).filter(models.Complaint.category_id.isnot(None)).count()


class _ComplaintStatRow:
    def __init__(self, label: str, count: int):
        self.label = label
        self.count = count


def get_complaint_stats_by_category(db: Session) -> list[_ComplaintStatRow]:
    rows = (
        db.query(models.ComplaintCategory.name, func.count(models.Complaint.id))
        .outerjoin(models.Complaint, models.Complaint.category_id == models.ComplaintCategory.id)
        .group_by(models.ComplaintCategory.name, models.ComplaintCategory.id)
        .order_by(models.ComplaintCategory.id)
        .all()
    )
    return [_ComplaintStatRow(label=row[0], count=row[1]) for row in rows]


def get_complaint_stats_by_address(db: Session) -> list[_ComplaintStatRow]:
    rows = (
        db.query(models.Complaint.address, func.count(models.Complaint.id))
        .filter(models.Complaint.address.isnot(None))
        .group_by(models.Complaint.address)
        .order_by(func.count(models.Complaint.id).desc())
        .all()
    )
    return [_ComplaintStatRow(label=row[0] or "未知", count=row[1]) for row in rows]


def get_complaint_stats_by_time(db: Session) -> list[_ComplaintStatRow]:
    period_expr = func.date_trunc("day", models.Complaint.complaint_time).label("period")
    rows = (
        db.query(period_expr, func.count(models.Complaint.id))
        .filter(models.Complaint.complaint_time.isnot(None))
        .group_by(period_expr)
        .order_by(period_expr)
        .all()
    )
    return [_ComplaintStatRow(label=row[0].strftime("%Y-%m-%d"), count=row[1]) for row in rows if row[0] is not None]


def search_complaints(
    db: Session,
    *,
    address: str | None = None,
    text: str | None = None,
    time_from: date | None = None,
    time_to: date | None = None,
    category_name: str | None = None,
    is_classified: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[models.Complaint], int]:
    query = db.query(models.Complaint).join(
        models.ComplaintCategory, models.Complaint.category_id == models.ComplaintCategory.id, isouter=True
    )
    if address:
        query = query.filter(models.Complaint.address.ilike(f"%{address}%"))
    if text:
        query = query.filter(models.Complaint.complaint_text.ilike(f"%{text}%"))
    if time_from:
        query = query.filter(models.Complaint.complaint_time >= datetime.combine(time_from, time.min))
    if time_to:
        query = query.filter(models.Complaint.complaint_time < datetime.combine(time_to + timedelta(days=1), time.min))
    if category_name:
        query = query.filter(models.ComplaintCategory.name == category_name)
    if is_classified is True:
        query = query.filter(models.Complaint.category_id.isnot(None))
    elif is_classified is False:
        query = query.filter(models.Complaint.category_id.is_(None))

    total = query.count()
    rows = (
        query.order_by(models.Complaint.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def list_feature_intros(db: Session, page_key: str | None = None) -> list[models.FeatureIntro]:
    query = db.query(models.FeatureIntro)
    if page_key:
        query = query.filter(models.FeatureIntro.page_key == page_key)
    return query.order_by(models.FeatureIntro.page_key, models.FeatureIntro.section_key).all()


def upsert_feature_intro(
    db: Session, page_key: str, section_key: str, data: schemas.FeatureIntroUpsert
) -> models.FeatureIntro:
    row = (
        db.query(models.FeatureIntro)
        .filter(models.FeatureIntro.page_key == page_key, models.FeatureIntro.section_key == section_key)
        .first()
    )
    if row:
        row.title = data.title
        row.content = data.content
    else:
        row = models.FeatureIntro(
            page_key=page_key,
            section_key=section_key,
            title=data.title,
            content=data.content,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


DEFAULT_FEATURE_INTROS: list[tuple[str, str, str]] = [
    ("app", "header", "站点说明"),
    ("complaints", "samples", "投诉样本查询"),
    ("complaints", "category", "按投诉类型"),
    ("complaints", "address", "按地区"),
    ("complaints", "time", "按时间（天）"),
    ("rag", "page", "RAG 检索"),
    ("rag", "import", "导入文档"),
    ("rag", "listByFile", "按文件名查"),
    ("rag", "search", "向量检索"),
    ("rag", "search-and-llm", "搜索+LLM"),
    ("ai-chat", "page", "AI 训练提问"),
    ("agent", "single", "单智能体"),
    ("agent", "sequential", "顺序模式"),
    ("agent", "routing", "路由模式"),
    ("agent", "reflection", "循环/反思模式"),
    ("meeting", "page", "会议整理"),
    ("smart-route", "page", "智能路由"),
    ("attendance", "punch", "人脸打卡"),
    ("attendance", "history", "打卡历史"),
    ("attendance", "persons", "已登记人员"),
    ("cobol-migrate", "page", "COBOL to Java 多 Agent 迁移流程演示"),
]


def seed_feature_intros(db: Session) -> list[models.FeatureIntro]:
    created: list[models.FeatureIntro] = []
    for page_key, section_key, title in DEFAULT_FEATURE_INTROS:
        exists = (
            db.query(models.FeatureIntro)
            .filter(models.FeatureIntro.page_key == page_key, models.FeatureIntro.section_key == section_key)
            .first()
        )
        if exists:
            continue
        row = models.FeatureIntro(page_key=page_key, section_key=section_key, title=title, content="")
        db.add(row)
        created.append(row)
    if created:
        db.commit()
        for row in created:
            db.refresh(row)
    return created
