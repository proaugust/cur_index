from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, defer

from app import models, schemas
from app.services.modules.chunk_table_ops import source_file_like_pattern


@dataclass(frozen=True)
class ComplaintFilterParams:
    time_from: date | None = None
    time_to: date | None = None
    category_name: str | None = None
    address: str | None = None
    classified: bool | None = None


def _complaint_query_with_category(db: Session):
    return db.query(models.Complaint).join(
        models.ComplaintCategory, models.Complaint.category_id == models.ComplaintCategory.id, isouter=True
    )


def _apply_complaint_filters(query, filters: ComplaintFilterParams | None):
    if not filters:
        return query
    if filters.address:
        query = query.filter(models.Complaint.address.ilike(f"%{filters.address}%"))
    if filters.time_from:
        query = query.filter(models.Complaint.complaint_time >= datetime.combine(filters.time_from, time.min))
    if filters.time_to:
        query = query.filter(
            models.Complaint.complaint_time < datetime.combine(filters.time_to + timedelta(days=1), time.min)
        )
    if filters.category_name:
        query = query.filter(models.ComplaintCategory.name == filters.category_name)
    if filters.classified is True:
        query = query.filter(models.Complaint.category_id.isnot(None))
    elif filters.classified is False:
        query = query.filter(models.Complaint.category_id.is_(None))
    return query


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


def list_source_files_page(
    db: Session,
    source_file: str | None = None,
    *,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[str], int]:
    query = db.query(models.DocumentChunk.source_file).distinct()
    file_pattern = source_file_like_pattern(source_file)
    if file_pattern:
        query = query.filter(models.DocumentChunk.source_file.ilike(file_pattern))
    query = query.order_by(models.DocumentChunk.source_file)
    total = int(query.count())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return [row[0] for row in rows], total


def get_document_chunks(
    db: Session,
    source_file: str | None = None,
    *,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[models.DocumentChunk], int]:
    query = db.query(models.DocumentChunk).options(
        defer(models.DocumentChunk.embedding, raiseload=True)
    )
    file_pattern = source_file_like_pattern(source_file)
    if file_pattern:
        query = query.filter(models.DocumentChunk.source_file.ilike(file_pattern))
    query = query.order_by(models.DocumentChunk.id)
    total = int(query.count())
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


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
    lang: str = "zh",
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
        lang=lang,
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


def clear_all_document_chunks(db: Session) -> int:
    """清空通用文档库全部切块。"""
    deleted = db.query(models.DocumentChunk).delete(synchronize_session=False)
    db.commit()
    return int(deleted)


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


def count_complaints(db: Session, filters: ComplaintFilterParams | None = None) -> int:
    query = _apply_complaint_filters(_complaint_query_with_category(db), filters)
    return query.count()


def count_classified_complaints(db: Session, filters: ComplaintFilterParams | None = None) -> int:
    query = _apply_complaint_filters(_complaint_query_with_category(db), filters)
    return query.filter(models.Complaint.category_id.isnot(None)).count()


class _ComplaintStatRow:
    def __init__(self, label: str, count: int):
        self.label = label
        self.count = count


def get_complaint_time_bounds(db: Session) -> tuple[datetime | None, datetime | None]:
    min_time = db.query(func.min(models.Complaint.complaint_time)).scalar()
    max_time = db.query(func.max(models.Complaint.complaint_time)).scalar()
    return min_time, max_time


def _has_active_filters(filters: ComplaintFilterParams | None) -> bool:
    if filters is None:
        return False
    return any(
        [
            filters.time_from is not None,
            filters.time_to is not None,
            filters.category_name,
            filters.address,
            filters.classified is not None,
        ]
    )


def get_complaint_stats_by_category(
    db: Session, filters: ComplaintFilterParams | None = None
) -> list[_ComplaintStatRow]:
    if not _has_active_filters(filters):
        rows = (
            db.query(models.ComplaintCategory.name, func.count(models.Complaint.id))
            .outerjoin(models.Complaint, models.Complaint.category_id == models.ComplaintCategory.id)
            .group_by(models.ComplaintCategory.name, models.ComplaintCategory.id)
            .order_by(models.ComplaintCategory.id)
            .all()
        )
        return [_ComplaintStatRow(label=row[0], count=row[1]) for row in rows]

    query = (
        db.query(models.ComplaintCategory.name, func.count(models.Complaint.id))
        .join(models.Complaint, models.Complaint.category_id == models.ComplaintCategory.id)
    )
    query = _apply_complaint_filters(query, filters)
    rows = query.group_by(models.ComplaintCategory.name, models.ComplaintCategory.id).order_by(
        func.count(models.Complaint.id).desc(), models.ComplaintCategory.id
    ).all()
    return [_ComplaintStatRow(label=row[0], count=row[1]) for row in rows if row[1] > 0]


def get_complaint_stats_by_address(
    db: Session, filters: ComplaintFilterParams | None = None
) -> list[_ComplaintStatRow]:
    query = db.query(models.Complaint.address, func.count(models.Complaint.id)).select_from(models.Complaint)
    if filters and filters.category_name:
        query = query.join(
            models.ComplaintCategory, models.Complaint.category_id == models.ComplaintCategory.id
        )
    query = _apply_complaint_filters(query, filters)
    rows = (
        query.filter(models.Complaint.address.isnot(None))
        .group_by(models.Complaint.address)
        .order_by(func.count(models.Complaint.id).desc())
        .all()
    )
    return [_ComplaintStatRow(label=row[0] or "未知", count=row[1]) for row in rows]


def get_complaint_stats_by_time(
    db: Session, filters: ComplaintFilterParams | None = None
) -> list[_ComplaintStatRow]:
    period_expr = func.date_trunc("day", models.Complaint.complaint_time).label("period")
    query = db.query(period_expr, func.count(models.Complaint.id)).select_from(models.Complaint)
    if filters and filters.category_name:
        query = query.join(
            models.ComplaintCategory, models.Complaint.category_id == models.ComplaintCategory.id
        )
    query = _apply_complaint_filters(query, filters)
    rows = (
        query.filter(models.Complaint.complaint_time.isnot(None))
        .group_by(period_expr)
        .order_by(period_expr)
        .all()
    )
    return [_ComplaintStatRow(label=row[0].strftime("%Y-%m-%d"), count=row[1]) for row in rows if row[0] is not None]


def get_complaint_stats_ranked(
    db: Session,
    *,
    filters: ComplaintFilterParams | None,
    group_by: str,
    rank: str,
    limit: int,
) -> list[_ComplaintStatRow]:
    if group_by == "address":
        rows = get_complaint_stats_by_address(db, filters)
    elif group_by == "category":
        rows = get_complaint_stats_by_category(db, filters)
    elif group_by == "day":
        rows = get_complaint_stats_by_time(db, filters)
    else:
        return []
    rows_sorted = sorted(rows, key=lambda row: row.count, reverse=rank == "max")
    return rows_sorted[:limit]


def search_complaints(
    db: Session,
    *,
    address: str | None = None,
    text: str | None = None,
    time_from: date | None = None,
    time_to: date | None = None,
    category_name: str | None = None,
    classified: bool | None = None,
    min_similarity: float | None = None,
    query_vector: list[float] | None = None,
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[tuple[models.Complaint, float | None]], int]:
    """返回 (投诉, 展示用相似度)。有 query_vector 时为查询↔投诉相似度，否则为归类分。"""
    filters = ComplaintFilterParams(
        address=address,
        time_from=time_from,
        time_to=time_to,
        category_name=category_name,
        classified=classified,
    )
    defer_embedding = defer(models.Complaint.embedding, raiseload=True)
    if query_vector is not None:
        distance_expr = models.Complaint.embedding.cosine_distance(query_vector)
        query = (
            db.query(models.Complaint, distance_expr.label("distance"))
            .options(defer_embedding)
            .join(
                models.ComplaintCategory,
                models.Complaint.category_id == models.ComplaintCategory.id,
                isouter=True,
            )
        )
        query = _apply_complaint_filters(query, filters)
        query = query.filter(models.Complaint.embedding.isnot(None))
        if min_similarity is not None:
            query = query.filter(distance_expr <= (1.0 - min_similarity))
        total = query.order_by(None).count()
        rows = (
            query.order_by(distance_expr.asc(), models.Complaint.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return [(row, round(1.0 - float(distance), 4)) for row, distance in rows], total

    query = _apply_complaint_filters(_complaint_query_with_category(db).options(defer_embedding), filters)
    if text:
        query = query.filter(models.Complaint.complaint_text.ilike(f"%{text}%"))
    if min_similarity is not None:
        query = query.filter(models.Complaint.similarity >= min_similarity)
    total = query.count()
    rows = (
        query.order_by(models.Complaint.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [(row, row.similarity) for row in rows], total


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


# (page_key, section_key, title, content)；seed 只插入缺失行，或给空 content 填默认，不覆盖已有文案
DEFAULT_FEATURE_INTROS: list[tuple[str, str, str, str]] = [
    (
        "app",
        "header",
        "站点说明",
        "本站是一套 AI 能力演示后台：投诉分析、RAG 检索、Agent、考勤等可从左侧菜单进入。点气泡可编辑各功能说明。",
    ),
    (
        "complaints",
        "samples",
        "投诉样本查询",
        "按地区、时间、正文语义检索投诉样本，可结合分类与相似度过滤，查看原始投诉文本。",
    ),
    (
        "complaints",
        "category",
        "按投诉类型",
        "按投诉类型聚合数量与占比，点击扇区可下钻到该类型的样本列表。",
    ),
    ("complaints", "address", "按地区", "按地区聚合投诉量，用于对比不同区域的投诉热度。"),
    ("complaints", "time", "按时间（天）", "按天查看投诉量趋势，便于发现集中爆发的时段。"),
    (
        "rag",
        "page",
        "RAG 检索",
        "根据提示词语义做检索：文本先向量化，再在向量库中按相似度召回相关切块。",
    ),
    (
        "rag",
        "import",
        "导入文档",
        "上传 UTF-8 文本，切块写入通用文档库 document_chunks，供后续检索与问答。",
    ),
    (
        "rag",
        "listByFile",
        "按文件名查",
        "列出已导入文件路径（去重）。可按文件名关键字过滤，本 Tab 不展示切块正文。",
    ),
    (
        "rag",
        "search",
        "混合检索，重排，top5",
        "对通用文档库做向量+全文混合检索，可选 C1 重排，默认返回最相关的 top 5 切块。",
    ),
    (
        "rag",
        "search-and-llm",
        "搜索+LLM",
        "先检索通用文档库相关切块，再用大模型润色成回答，并保留原始出处便于核对。",
    ),
    ("rag", "clear", "清空文档库", "删除通用文档库 document_chunks 中的全部切块，操作不可恢复，请确认后再执行。"),
    (
        "rag",
        "corpora-import",
        "资料库导入",
        "中文\n将 .md/.txt/.zip 异步导入业务知识库 document_business_chunks。资料名必填（可手动填，默认取 ZIP 内文件夹名或文件名）。\n\n日文\n.md/.txt/.zip を業務ナレッジ庫 document_business_chunks へ非同期取り込みます。資料名は必須です（ZIP 内フォルダ名またはファイル名が既定値）。",
    ),
    (
        "rag",
        "corpora-import-job",
        "资料库导入任务",
        "中文\n查询异步导入进度：pending / running / done / failed。导入大 ZIP 时可轮询本接口。\n\n日文\n非同期取り込みの進捗（pending / running / done / failed）を確認します。",
    ),
    (
        "rag",
        "corpora-list",
        "资料库列表",
        "中文\n列出已注册的业务知识库（切块均在 document_business_chunks），可按分类过滤。\n\n日文\n登録済みの業務ナレッジ庫一覧です。分類で絞り込めます。",
    ),
    (
        "rag",
        "corpora-listByFile",
        "按文件名查",
        "中文\n列出资料库已导入的文件路径（去重）。资料名或文件名可留空查全部，本 Tab 不展示切块正文。\n\n日文\n資料庫に取り込まれたファイルパス（重複除外）を一覧します。本文チャンクは表示しません。",
    ),
    (
        "rag",
        "corpora-files",
        "资料库文件",
        "中文\n查询某资料库下已导入的文件名；资料名留空则查全部资料库。\n\n日文\n指定資料庫（空なら全部）に取り込まれたファイル名を照会します。",
    ),
    (
        "rag",
        "corpora-suggest-filters",
        "检索过滤建议",
        "中文\n根据问题关键词规则建议分类、资料库等过滤条件，可改后再检索。\n\n日文\n質問キーワードから分類・資料庫などのフィルタ候補を提案します。",
    ),
    (
        "rag",
        "corpora-search",
        "资料库检索",
        "中文\n对业务资料库做向量/混合检索，可按分类或多库过滤；问题留空则返回默认切块列表。\n\n日文\n業務資料庫のベクトル／ハイブリッド検索です。分類・複数庫で絞り込めます。",
    ),
    (
        "rag",
        "corpora-search-llm",
        "资料库检索+LLM",
        "中文\n业务资料库检索后再用大模型润色回答，并保留原始出处。\n\n日文\n業務資料庫を検索し、LLM で回答を整えます。出典も残します。",
    ),
    (
        "rag",
        "corpora-delete",
        "资料库删除",
        "中文\n删除资料库注册记录，并清空该资料名在 document_business_chunks 中的切块（不 DROP 共享表）。\n\n日文\n資料庫の登録を削除し、当該資料名のチャンクを空にします（共有表は DROP しません）。",
    ),
    (
        "rag",
        "corpora-browse",
        "资料库浏览检索",
        "中文\n可视化浏览业务知识库：选资料库、看文件与切块，并做语义检索。导入请用「资料库导入」Tab。\n\n日文\n業務ナレッジ庫を画面で閲覧・検索します。取り込みは「資料庫导入」タブを使います。",
    ),
    (
        "ai-chat",
        "page",
        "AI 训练提问",
        "选择场景或自定义问题，调用大模型作答，用于对比不同提示与回复风格。",
    ),
    (
        "agent",
        "single",
        "单智能体",
        "单个 Agent 直接使用工具完成问答，适合步骤少、目标明确的问题。",
    ),
    (
        "agent",
        "sequential",
        "顺序模式",
        "规划 → 执行 → 总结按固定流水线依次调用多个 Agent。",
    ),
    (
        "agent",
        "routing",
        "路由模式",
        "先由路由 Agent 判断意图，再交给对应专家 Agent 作答。",
    ),
    (
        "agent",
        "reflection",
        "循环/反思模式",
        "生成、评审、修订循环迭代，直到回答通过评审或达到轮次上限。",
    ),
    ("meeting", "page", "会议整理", "粘贴会议记录，按简洁或正式风格整理纪要与待办。"),
    (
        "smart-route",
        "page",
        "智能路由",
        "根据问题意图路由到天气、考勤人员等不同后端能力，并展示路由结果。",
    ),
    (
        "attendance",
        "punch",
        "人脸打卡",
        "摄像头采集人脸并与已登记人员比对完成打卡（本地需人脸模型；HF 上可能不可用）。",
    ),
    ("attendance", "history", "打卡历史", "按人员查看打卡记录，可删除单条或批量清理。"),
    ("attendance", "persons", "已登记人员", "管理已录入人脸的人员名单，支持新增与删除。"),
    (
        "cobol-migrate",
        "page",
        "COBOL to Java 多 Agent 迁移流程演示",
        "多 Agent 演示 COBOL 到 Java 的解析、翻译、校验与测试报告流程，可逐步或一键跑通。",
    ),
    (
        "zha-jinhua",
        "page",
        "炸金花 AI 对局",
        "人机炸金花对局演示：发牌、跟注/弃牌，并展示 AI 裁判与底池流水。",
    ),
]


def seed_feature_intros(db: Session) -> list[models.FeatureIntro]:
    touched: list[models.FeatureIntro] = []
    for page_key, section_key, title, content in DEFAULT_FEATURE_INTROS:
        row = (
            db.query(models.FeatureIntro)
            .filter(models.FeatureIntro.page_key == page_key, models.FeatureIntro.section_key == section_key)
            .first()
        )
        if row:
            if not (row.content or "").strip() and content:
                row.content = content
                if not (row.title or "").strip():
                    row.title = title
                touched.append(row)
            continue
        row = models.FeatureIntro(page_key=page_key, section_key=section_key, title=title, content=content)
        db.add(row)
        touched.append(row)
    if touched:
        db.commit()
        for row in touched:
            db.refresh(row)
    return touched
