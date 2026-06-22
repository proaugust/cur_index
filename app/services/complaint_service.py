import logging

from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.services.complaint_categories import CATEGORY_SEEDS, LOGISTICS_DELAY, dumps_seed_phrases
from app.services.complaint_generator import generate_logistics_complaints
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
        texts = generate_logistics_complaints(count)
        logger.info("开始向量化 %s 条文本", len(texts))
        vectors = embed_texts(texts, show_progress=True)

        rows = [
            models.Complaint(content=text, embedding=vector)
            for text, vector in zip(texts, vectors)
        ]
        logger.info("写入数据库")
        self.db.add_all(rows)
        self.db.commit()
        logger.info("投诉造数完成，插入 %s 条", len(rows))
        return schemas.ComplaintSeedResult(inserted=len(rows))

    def classify_all(self) -> schemas.ComplaintClassifyResult:
        categories = crud.get_complaint_categories(self.db)
        complaints = crud.get_unclassified_complaints(self.db)
        if not categories:
            logger.warning("无可用分类，跳过归类")
            return schemas.ComplaintClassifyResult(
                classified=0,
                logistics_delay_count=0,
                logistics_delay_percentage=0.0,
            )

        total = len(complaints)
        logger.info("开始归类：%s 条待处理，%s 个分类", total, len(categories))

        classified = 0
        logistics_delay_count = 0
        for index, complaint in enumerate(complaints, start=1):
            if not complaint.embedding:
                continue
            best_category = None
            best_score = -1.0
            for category in categories:
                if not category.embedding:
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
            if best_category.name == LOGISTICS_DELAY:
                logistics_delay_count += 1

            if index % 50 == 0 or index == total:
                logger.info(
                    "归类进度 %s/%s，已归类 %s 条",
                    index,
                    total,
                    classified,
                )

        self.db.commit()
        percentage = (logistics_delay_count / classified * 100) if classified else 0.0
        logger.info(
            "归类完成：共 %s 条，物流延误 %s 条 (%.2f%%)",
            classified,
            logistics_delay_count,
            percentage,
        )
        return schemas.ComplaintClassifyResult(
            classified=classified,
            logistics_delay_count=logistics_delay_count,
            logistics_delay_percentage=round(percentage, 2),
        )

    def get_stats(self) -> schemas.ComplaintStatsReport:
        total = crud.count_complaints(self.db)
        classified = crud.count_classified_complaints(self.db)
        rows = crud.get_complaint_stats(self.db)
        categories = [
            schemas.ComplaintStatsItem(
                category_id=row.category_id,
                category_name=row.category_name,
                count=row.count,
                percentage=round(row.count / total * 100, 2) if total else 0.0,
            )
            for row in rows
        ]
        return schemas.ComplaintStatsReport(
            total=total,
            classified=classified,
            unclassified=total - classified,
            categories=categories,
        )

    def get_samples(
        self,
        category_name: str | None = None,
        limit: int = 10,
    ) -> list[schemas.ComplaintRead]:
        rows = crud.get_complaint_samples(self.db, category_name=category_name, limit=limit)
        return [
            schemas.ComplaintRead(
                id=row.id,
                content=row.content,
                category_id=row.category_id,
                category_name=row.category.name if row.category else None,
                similarity=row.similarity,
            )
            for row in rows
        ]
