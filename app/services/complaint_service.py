import logging
from datetime import date

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.complaint_categories import CATEGORY_SEEDS, dumps_seed_phrases
from app.services.complaint_generator import generate_complaints
from app.services.embedding import cosine_similarity, embed_texts, mean_vector

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
                if best_category is not None:
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

    def get_stats(self) -> schemas.ComplaintStatsReport:
        total = crud.count_complaints(self.db)
        classified = crud.count_classified_complaints(self.db)
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
                    percentage=round(row.count / total * 100, 2) if total else 0.0,
                )
                for row in rows
            ]

        return schemas.ComplaintStatsReport(
            total=total,
            classified=classified,
            unclassified=total - classified,
            dimensions=dimensions,
            by_category=to_items(crud.get_complaint_stats_by_category(self.db)),
            by_address=to_items(crud.get_complaint_stats_by_address(self.db)),
            by_time=to_items(crud.get_complaint_stats_by_time(self.db)),
        )

    def search_samples(
        self,
        *,
        address: str | None = None,
        text: str | None = None,
        time_from: date | None = None,
        time_to: date | None = None,
        category_name: str | None = None,
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
