"""Insight 造数编排服务。"""

import logging
import random
import time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import insight as crud_insight
from app.models.insight import DimUserProfile
from app.schemas.insight import (
    InsightComplaintPreview,
    InsightPreset,
    InsightSeedPreviewResult,
    InsightSeedResetResult,
    InsightSeedSamplesResult,
    InsightSeedStatus,
    InsightSeedPresetInfo,
    InsightSeedUsersResult,
)
from app.services.modules.insight.constants import SAMPLE_BATCH_SIZE, SEED_PRESETS, USER_BATCH_SIZE
from app.services.modules.insight.seed.complaint_generator import build_complaint_row, build_preview_row
from app.services.modules.insight.seed.profile_generator import generate_profile_row, strip_seed_meta
from app.services.modules.insight.seed.survey_generator import build_survey_row
from app.services.modules.insight.vector_service import embed_complaint_texts

logger = logging.getLogger(__name__)
_PAIR_RANDOM = random.Random(99)


class InsightSeedService:
    def __init__(self, db: Session):
        self.db = db

    def get_status(self) -> InsightSeedStatus:
        return InsightSeedStatus(**crud_insight.get_seed_status(self.db))

    def list_presets(self) -> list[InsightSeedPresetInfo]:
        return [
            InsightSeedPresetInfo(key=key, users=vals["users"], complaints=vals["complaints"], touchpoints=vals["touchpoints"])
            for key, vals in SEED_PRESETS.items()
        ]

    def seed_users(self, preset: InsightPreset = "demo") -> InsightSeedUsersResult:
        target = SEED_PRESETS[preset]["users"]
        crud_insight.sync_user_seq(self.db)

        started = time.perf_counter()
        inserted = 0
        remaining = target
        while remaining > 0:
            batch_size = min(USER_BATCH_SIZE, remaining)
            rows = [generate_profile_row() for _ in range(batch_size)]
            inserted += crud_insight.bulk_insert_profiles(self.db, rows)
            remaining -= batch_size
            logger.info("Insight 用户画像追加进度 %s/%s", inserted, target)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return InsightSeedUsersResult(preset=preset, inserted=inserted, elapsed_ms=elapsed_ms)

    def seed_samples(self, preset: InsightPreset = "demo") -> InsightSeedSamplesResult:
        plan = SEED_PRESETS[preset]
        sample_count = max(plan["complaints"], plan["touchpoints"])
        pairs = crud_insight.list_category_pairs()
        if not pairs:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="投诉分类未配置")

        crud_insight.sync_complaint_seq(self.db)
        started = time.perf_counter()
        inserted = self._insert_samples(sample_count, pairs)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return InsightSeedSamplesResult(
            preset=preset,
            complaints_inserted=inserted,
            touchpoints_inserted=inserted,
            samples_inserted=inserted,
            elapsed_ms=elapsed_ms,
        )

    def _ensure_customer_reset_allowed(self) -> None:
        status_data = crud_insight.get_seed_status(self.db)
        if status_data["samples"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"已有 {status_data['samples']} 条样本数据，请先在「注入样本数据」页清空样本",
            )
        if status_data["snapshots"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"已有 {status_data['snapshots']} 条快照数据，请先在「注入样本数据」页清空样本",
            )

    def reset_users(self) -> InsightSeedResetResult:
        self._ensure_customer_reset_allowed()
        return InsightSeedResetResult(cleared=crud_insight.clear_user_data(self.db))

    def reset_samples(self) -> InsightSeedResetResult:
        cleared = crud_insight.clear_sample_data(self.db)
        cleared.update(crud_insight.clear_snapshot_data(self.db))
        return InsightSeedResetResult(cleared=cleared)

    def preview_complaints(self, count: int = 3) -> InsightSeedPreviewResult:
        pairs = crud_insight.list_category_pairs()
        if not pairs:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="投诉分类未配置")
        previews: list[InsightComplaintPreview] = []
        for _ in range(count):
            pair = _PAIR_RANDOM.choice(pairs)
            user = strip_seed_meta(generate_profile_row())
            row = build_preview_row(pair, user)
            previews.append(InsightComplaintPreview(**row))
        return InsightSeedPreviewResult(items=previews)

    def _insert_samples(self, count: int, pairs: list[dict]) -> int:
        users = self._sample_user_rows(count)
        inserted = 0
        for offset in range(0, len(users), SAMPLE_BATCH_SIZE):
            chunk = users[offset : offset + SAMPLE_BATCH_SIZE]
            rows = [
                {
                    **build_survey_row(),
                    **build_complaint_row(_PAIR_RANDOM.choice(pairs), item),
                }
                for item in chunk
            ]
            vectors = embed_complaint_texts([row["raw_text"] for row in rows], show_progress=True)
            for row, vector in zip(rows, vectors):
                row["complaint_vector"] = vector
            inserted += crud_insight.bulk_insert_complaint_touchpoints(self.db, rows)
        return inserted

    def _sample_user_rows(self, count: int) -> list[dict]:
        users = crud_insight.random_user_rows(self.db, count)
        missing = count - len(users)
        if missing <= 0:
            return users
        users.extend(generate_profile_row() for _ in range(missing))
        return users
