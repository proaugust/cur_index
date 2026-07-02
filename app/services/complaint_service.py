import json
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.services.complaint_categories import CATEGORY_SEEDS, dumps_seed_phrases
from app.services.complaint_category_namer import suggest_complaint_category
from app.services.complaint_query_parser import parse_complaint_query
from app.services.complaint_generator import generate_complaints
from app.services.complaint_settings import get_classify_threshold, set_classify_threshold
from app.services.embedding import cosine_similarity, embed_text, embed_texts, mean_vector

logger = logging.getLogger(__name__)


class ComplaintService:
    def __init__(self, db: Session):
        self.db = db

    def init_categories(self) -> list[schemas.ComplaintCategoryRead]:
        logger.info("初始化投诉分类：清空旧数据")
        crud.clear_complaints(self.db)
        crud.clear_complaint_categories(self.db)

        created: list[models.ComplaintCategory] = []
        total = len(CATEGORY_SEEDS)
        for index, (name, meta) in enumerate(CATEGORY_SEEDS.items(), start=1):
            logger.info("嵌入分类种子 [%s/%s] %s", index, total, name)
            seed_vectors = embed_texts(meta["seed_phrases"])
            category = models.ComplaintCategory(
                name=name,
                description=meta["description"],
                seed_phrases=dumps_seed_phrases(meta["seed_phrases"]),
                embedding=mean_vector(seed_vectors),
            )
            created.append(category)

        logger.info("写入 %s 个分类", len(created))
        self.db.add_all(created)
        self.db.commit()
        for item in created:
            self.db.refresh(item)
        logger.info("分类初始化完成")
        return created

    def seed_complaints(self, count: int = 500) -> schemas.ComplaintSeedResult:
        logger.info("生成 %s 条投诉文本", count)
        categories = [c for c in crud.get_complaint_categories(self.db) if c.embedding is not None]
        if not categories:
            logger.warning("complaint_categories 无可用 embedding，请先调用 init-categories")

        items = generate_complaints(count)
        texts = [item.complaint_text for item in items]
        logger.info("向量化 %s 条投诉文本", len(texts))
        vectors = embed_texts(texts, show_progress=True)

        rows: list[models.Complaint] = []
        for item, vector in zip(items, vectors):
            category_id = None
            similarity = None
            if categories:
                best_category = None
                best_score = -1.0
                for category in categories:
                    score = cosine_similarity(vector, category.embedding)
                    if score > best_score:
                        best_score = score
                        best_category = category
                if best_category is not None and best_score >= get_classify_threshold():
                    category_id = best_category.id
                    similarity = best_score

            rows.append(
                models.Complaint(
                    complaint_text=item.complaint_text,
                    address=item.address,
                    complaint_time=item.complaint_time,
                    embedding=vector,
                    category_id=category_id,
                    similarity=similarity,
                )
            )

        logger.info("写入数据库")
        self.db.add_all(rows)
        self.db.commit()
        classified = sum(1 for row in rows if row.category_id is not None)
        logger.info("投诉造数完成，插入 %s 条（已归类 %s 条）", len(rows), classified)
        return schemas.ComplaintSeedResult(inserted=len(rows))

    def embed_complaints(self) -> schemas.ComplaintEmbedResult:
        complaints = crud.get_complaints_without_embedding(self.db)
        skipped = crud.count_complaints(self.db) - len(complaints)
        if not complaints:
            logger.info("无待向量化投诉")
            return schemas.ComplaintEmbedResult(embedded=0, skipped=skipped)

        total = len(complaints)
        logger.info("开始向量化 %s 条投诉文本", total)
        texts = [complaint.complaint_text for complaint in complaints]
        vectors = embed_texts(texts, show_progress=True)
        for index, (complaint, vector) in enumerate(zip(complaints, vectors), start=1):
            complaint.embedding = vector
            if index % 50 == 0 or index == total:
                logger.info("向量化进度 %s/%s", index, total)

        self.db.commit()
        logger.info("向量化完成，写入 %s 条 vector embedding", total)
        return schemas.ComplaintEmbedResult(embedded=total, skipped=skipped)

    def classify_all(self) -> schemas.ComplaintClassifyResult:
        categories = crud.get_complaint_categories(self.db)
        complaints = crud.get_unclassified_complaints(self.db)
        if not categories:
            logger.warning("无可用分类，跳过归类")
            return schemas.ComplaintClassifyResult(classified=0, by_category=[])

        total = len(complaints)
        logger.info("开始归类：%s 条待处理，%s 个分类", total, len(categories))

        category_counts: dict[str, int] = {category.name: 0 for category in categories}
        classified = 0
        for index, complaint in enumerate(complaints, start=1):
            if complaint.embedding is None:
                continue
            best_category = None
            best_score = -1.0
            for category in categories:
                if category.embedding is None:
                    continue
                score = cosine_similarity(complaint.embedding, category.embedding)
                if score > best_score:
                    best_score = score
                    best_category = category
            if best_category is None:
                continue
            if best_score < get_classify_threshold():
                continue

            complaint.category_id = best_category.id
            complaint.similarity = best_score
            classified += 1
            category_counts[best_category.name] = category_counts.get(best_category.name, 0) + 1

            if index % 50 == 0 or index == total:
                logger.info("归类进度 %s/%s，已归类 %s 条", index, total, classified)

        self.db.commit()
        by_category = [
            schemas.ComplaintClassifyCategoryCount(
                category_name=name,
                count=count,
                percentage=round(count / classified * 100, 2) if classified else 0.0,
            )
            for name, count in category_counts.items()
        ]
        logger.info("归类完成：共 %s 条，分布 %s", classified, {item.category_name: item.count for item in by_category})
        return schemas.ComplaintClassifyResult(classified=classified, by_category=by_category)

    def _filters_from_schema(self, filters: schemas.ComplaintStatsFilters | None) -> crud.ComplaintFilterParams | None:
        if filters is None:
            return None
        return crud.ComplaintFilterParams(
            time_from=filters.time_from,
            time_to=filters.time_to,
            category_name=filters.category_name,
            address=filters.address,
        )

    def get_stats(self, q: str | None = None) -> schemas.ComplaintStatsReport:
        parsed_query: schemas.ComplaintStatsParsedQuery | None = None
        filter_params: crud.ComplaintFilterParams | None = None

        min_time, max_time = crud.get_complaint_time_bounds(self.db)
        data_time_from = min_time.date() if min_time else None
        data_time_to = max_time.date() if max_time else None

        if q and q.strip():
            parsed_query = parse_complaint_query(
                q.strip(),
                data_time_from=data_time_from,
                data_time_to=data_time_to,
            )
            filter_params = self._filters_from_schema(parsed_query.filters)

        has_filters = crud._has_active_filters(filter_params)
        scope_total = crud.count_complaints(self.db, filter_params if has_filters else None)
        classified = crud.count_classified_complaints(self.db, filter_params if has_filters else None)

        ranked_rows: list = []
        if parsed_query and parsed_query.intent == "stats" and parsed_query.group_by:
            ranked_rows = crud.get_complaint_stats_ranked(
                self.db,
                filters=filter_params,
                group_by=parsed_query.group_by,
                rank=parsed_query.rank,
                limit=parsed_query.limit,
            )

        dimensions = [
            schemas.ComplaintStatsDimension(
                key="category",
                field="category_id → complaint_categories.name",
                label="投诉类型",
                group_by="GROUP BY complaint_categories.name",
            ),
            schemas.ComplaintStatsDimension(
                key="address",
                field="address",
                label="地区",
                group_by="GROUP BY address",
            ),
            schemas.ComplaintStatsDimension(
                key="time",
                field="complaint_time",
                label="时间",
                group_by="GROUP BY date_trunc('day', complaint_time)",
            ),
        ]

        def to_items(rows: list) -> list[schemas.ComplaintStatsCountItem]:
            return [
                schemas.ComplaintStatsCountItem(
                    label=row.label,
                    count=row.count,
                    percentage=round(row.count / scope_total * 100, 2) if scope_total else 0.0,
                )
                for row in rows
            ]

        active_filters = filter_params if has_filters else None
        return schemas.ComplaintStatsReport(
            total=scope_total,
            classified=classified,
            unclassified=scope_total - classified,
            dimensions=dimensions,
            by_category=to_items(crud.get_complaint_stats_by_category(self.db, active_filters)),
            by_address=to_items(crud.get_complaint_stats_by_address(self.db, active_filters)),
            by_time=to_items(crud.get_complaint_stats_by_time(self.db, active_filters)),
            parsed_query=parsed_query,
            total_in_scope=scope_total if has_filters else None,
            ranked=to_items(ranked_rows),
            data_time_from=data_time_from,
            data_time_to=data_time_to,
        )

    def search_samples(
        self,
        *,
        address: str | None = None,
        text: str | None = None,
        time_from: date | None = None,
        time_to: date | None = None,
        category_name: str | None = None,
        classified: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> schemas.ComplaintSamplesPage:
        rows, total = crud.search_complaints(
            self.db,
            address=address,
            text=text,
            time_from=time_from,
            time_to=time_to,
            category_name=category_name,
            classified=classified,
            page=page,
            page_size=page_size,
        )
        items = [
            schemas.ComplaintRead(
                id=row.id,
                complaint_text=row.complaint_text,
                address=row.address,
                complaint_time=row.complaint_time,
                category_id=row.category_id,
                category_name=row.category.name if row.category else None,
                similarity=row.similarity,
            )
            for row in rows
        ]
        return schemas.ComplaintSamplesPage(items=items, total=total, page=page, page_size=page_size)

    def _score_categories(
        self, vector: list[float], categories: list[models.ComplaintCategory]
    ) -> list[tuple[models.ComplaintCategory, float]]:
        scored: list[tuple[models.ComplaintCategory, float]] = []
        for category in categories:
            if category.embedding is None:
                continue
            scored.append((category, cosine_similarity(vector, category.embedding)))
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored

    def _find_category_by_name_similarity(
        self, name: str, categories: list[models.ComplaintCategory]
    ) -> models.ComplaintCategory | None:
        if not name:
            return None
        name_vector = embed_text(name)
        best_category = None
        best_score = -1.0
        for category in categories:
            if category.embedding is None:
                continue
            score = cosine_similarity(name_vector, category.embedding)
            if score > best_score:
                best_score = score
                best_category = category
        if best_category is not None and best_score >= settings.complaint_name_dedupe_threshold:
            return best_category
        return None

    def _to_complaint_read(self, complaint: models.Complaint) -> schemas.ComplaintRead:
        return schemas.ComplaintRead(
            id=complaint.id,
            complaint_text=complaint.complaint_text,
            address=complaint.address,
            complaint_time=complaint.complaint_time,
            category_id=complaint.category_id,
            category_name=complaint.category.name if complaint.category else None,
            similarity=complaint.similarity,
        )

    def create_complaint(self, payload: schemas.ComplaintCreate) -> schemas.ComplaintCreateResult:
        complaint_text = payload.complaint_text.strip()
        vector = embed_text(complaint_text)
        categories = [c for c in crud.get_complaint_categories(self.db) if c.embedding is not None]
        scored = self._score_categories(vector, categories)

        best_category = scored[0][0] if scored else None
        best_score = scored[0][1] if scored else -1.0
        category_created = False
        assigned_category: models.ComplaintCategory | None = None
        similarity: float | None = None

        if best_category is not None and best_score >= get_classify_threshold():
            assigned_category = best_category
            similarity = round(best_score, 4)
        else:
            suggested_name, description = suggest_complaint_category(
                complaint_text, existing_names=[category.name for category in categories]
            )
            merge_target = self._find_category_by_name_similarity(suggested_name, categories)
            if merge_target is not None:
                assigned_category = merge_target
                similarity = round(cosine_similarity(vector, merge_target.embedding), 4)
            else:
                existing = crud.get_complaint_category_by_name(self.db, suggested_name)
                if existing is not None:
                    assigned_category = existing
                    similarity = round(cosine_similarity(vector, existing.embedding), 4) if existing.embedding else None
                else:
                    assigned_category = crud.create_complaint_category(
                        self.db,
                        name=suggested_name,
                        description=description,
                        seed_phrases=dumps_seed_phrases([complaint_text]),
                        embedding=vector,
                    )
                    category_created = True
                    similarity = 1.0
                    categories.append(assigned_category)
                    scored = self._score_categories(vector, categories)

        complaint = crud.create_complaint(
            self.db,
            complaint_text=complaint_text,
            address=payload.address,
            complaint_time=payload.complaint_time or datetime.utcnow(),
            embedding=vector,
            category_id=assigned_category.id if assigned_category else None,
            similarity=similarity,
        )
        self.db.refresh(complaint)

        category_scores = [
            schemas.ComplaintCategoryScore(
                category_id=category.id,
                category_name=category.name,
                similarity=round(score, 4),
            )
            for category, score in scored
        ]

        logger.info(
            "新增投诉 id=%s category=%s created=%s similarity=%s",
            complaint.id,
            assigned_category.name if assigned_category else None,
            category_created,
            similarity,
        )
        return schemas.ComplaintCreateResult(
            complaint=self._to_complaint_read(complaint),
            category_created=category_created,
            assigned_category_id=assigned_category.id if assigned_category else None,
            assigned_category_name=assigned_category.name if assigned_category else None,
            similarity=similarity,
            category_scores=category_scores,
        )

    def list_categories(self, *, name: str | None = None) -> list[schemas.ComplaintCategoryDetail]:
        rows = crud.list_complaint_categories(self.db, name=name)
        items: list[schemas.ComplaintCategoryDetail] = []
        for category, complaint_count in rows:
            try:
                seed_phrases = json.loads(category.seed_phrases) if category.seed_phrases else []
            except json.JSONDecodeError:
                seed_phrases = [category.seed_phrases] if category.seed_phrases else []
            if not isinstance(seed_phrases, list):
                seed_phrases = [str(seed_phrases)]
            items.append(
                schemas.ComplaintCategoryDetail(
                    id=category.id,
                    name=category.name,
                    description=category.description,
                    seed_phrases=[str(item) for item in seed_phrases],
                    complaint_count=complaint_count,
                    has_embedding=category.embedding is not None,
                )
            )
        return items

    def get_settings(self) -> schemas.ComplaintSettings:
        return schemas.ComplaintSettings(classify_threshold=get_classify_threshold())

    def update_settings(self, payload: schemas.ComplaintSettingsUpdate) -> schemas.ComplaintSettings:
        threshold = set_classify_threshold(payload.classify_threshold)
        logger.info("投诉归类阈值已更新为 %s", threshold)
        return schemas.ComplaintSettings(classify_threshold=threshold)
