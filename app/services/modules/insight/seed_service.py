"""Insight 造数编排：注入客户/样本分开；「合并样本」才把样本升成客户（1:1），评估用带 sample_satisfaction 的客户。"""

import logging
import random
import time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud import insight as crud_insight
from app.schemas.insight import (
    InsightComplaintPreview,
    InsightPreset,
    InsightSeedPreviewResult,
    InsightSeedPromoteSamplesResult,
    InsightSeedResetResult,
    InsightSeedSamplesResult,
    InsightSeedStatus,
    InsightSeedPresetInfo,
    InsightSeedUsersResult,
)
from app.services.modules.insight.churn_label_service import InsightChurnLabelService
from app.services.modules.insight.constants import SAMPLE_BATCH_SIZE, SEED_PRESETS, USER_BATCH_SIZE
from app.services.modules.insight.seed.complaint_generator import build_complaint_row, build_preview_row
from app.services.modules.insight.seed.profile_generator import generate_profile_row, strip_seed_meta
from app.services.modules.insight.seed.survey_generator import build_survey_row
from app.services.modules.insight.stats_cache import (
    get_cached_seed_status,
    invalidate_insight_stats_cache,
    set_cached_seed_status,
)
from app.services.modules.insight.vector_service import get_seed_template_vectors, vector_for_seed_template

logger = logging.getLogger(__name__)
_PAIR_RANDOM = random.Random(99)


class InsightSeedService:
    def __init__(self, db: Session):
        self.db = db

    def get_status(self, *, refresh: bool = False) -> InsightSeedStatus:
        if not refresh:
            cached = get_cached_seed_status()
            if cached is not None:
                return cached
        status = InsightSeedStatus(**crud_insight.get_seed_status(self.db))
        set_cached_seed_status(status)
        return status

    def list_presets(self) -> list[InsightSeedPresetInfo]:
        return [
            InsightSeedPresetInfo(key=key, users=vals["users"], complaints=vals["complaints"], touchpoints=vals["touchpoints"])
            for key, vals in SEED_PRESETS.items()
        ]

    def seed_users(
        self, preset: InsightPreset = "demo", count: int | None = None
    ) -> InsightSeedUsersResult:
        """仅追加独立客户。起号前 sync_user_seq（取客户+样本 max）；勿与造样本同时跑。"""
        from app.models.insight import DimUserProfile

        crud_insight.sync_user_seq(self.db)
        started = time.perf_counter()
        current = crud_insight.count_table(self.db, DimUserProfile)
        remaining = count if count is not None else SEED_PRESETS[preset]["users"]
        progress_total = current + remaining
        inserted = 0
        while remaining > 0:
            batch_size = min(USER_BATCH_SIZE, remaining)
            rows = [generate_profile_row() for _ in range(batch_size)]
            inserted += crud_insight.bulk_insert_profiles(self.db, rows)
            remaining -= batch_size
            logger.info(
                "Insight 用户画像进度 +%s → %s/%s",
                batch_size,
                current + inserted,
                progress_total,
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        invalidate_insight_stats_cache()
        return InsightSeedUsersResult(
            preset=preset,
            inserted=inserted,
            elapsed_ms=elapsed_ms,
        )

    def seed_samples(
        self, preset: InsightPreset = "demo", count: int | None = None
    ) -> InsightSeedSamplesResult:
        """仅追加样本。起号前 sync_user_seq；勿与造客户同时跑。合并走 promote_samples。"""
        plan = SEED_PRESETS[preset]
        if count is not None:
            sample_count = count
        else:
            sample_count = max(plan["complaints"], plan["touchpoints"])
        pairs = crud_insight.list_category_pairs()
        if not pairs:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="投诉分类未配置")

        crud_insight.sync_user_seq(self.db)
        crud_insight.sync_complaint_seq(self.db)
        started = time.perf_counter()
        inserted = self._insert_samples(sample_count, pairs)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        invalidate_insight_stats_cache()
        return InsightSeedSamplesResult(
            preset=preset,
            complaints_inserted=inserted,
            touchpoints_inserted=inserted,
            samples_inserted=inserted,
            elapsed_ms=elapsed_ms,
        )

    def promote_samples(self) -> InsightSeedPromoteSamplesResult:
        """将库内样本按自身 user_id 升成客户（1 样本 = 1 客户，与已有客户并存）。"""
        from app.services.modules.insight.analysis_log_writer import record_seed_promote_log

        started = time.perf_counter()
        promote_stats: dict = {"promoted": 0, "profiles_upserted": 0, "skipped": 0, "user_ids": []}
        churn_labels = 0
        try:
            promote_stats = crud_insight.promote_samples_to_customers(self.db)
            new_ids = set(promote_stats.get("user_ids") or [])
            if new_ids:
                churn_labels = InsightChurnLabelService(self.db).seed_synthetic(user_ids=new_ids)
                logger.info(
                    "Insight 样本合并客户 promoted=%s profiles=%s churn_labels=%s",
                    promote_stats["promoted"],
                    promote_stats["profiles_upserted"],
                    churn_labels,
                )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            invalidate_insight_stats_cache()
            record_seed_promote_log(
                status="completed",
                answer=(
                    f"合并样本完成：升客户 {promote_stats['profiles_upserted']} 名"
                    f"（跳过 {promote_stats.get('skipped', 0)}），合成标签 {churn_labels} 条"
                ),
                latency_ms=elapsed_ms,
                tools_trace={
                    "samples_merged": promote_stats["promoted"],
                    "profiles_upserted": promote_stats["profiles_upserted"],
                    "skipped": promote_stats.get("skipped", 0),
                    "churn_labels_inserted": churn_labels,
                },
            )
            return InsightSeedPromoteSamplesResult(
                samples_merged=promote_stats["promoted"],
                profiles_upserted=promote_stats["profiles_upserted"],
                churn_labels_inserted=churn_labels,
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            logger.exception("Insight 合并样本失败")
            record_seed_promote_log(
                status="failed",
                answer=f"合并样本失败：{exc}",
                latency_ms=elapsed_ms,
                tools_trace={
                    "samples_merged": promote_stats.get("promoted", 0),
                    "profiles_upserted": promote_stats.get("profiles_upserted", 0),
                },
                exc=exc,
            )
            raise

    def reset_users(self) -> InsightSeedResetResult:
        """仅清空客户主表；样本/快照独立，不强制先清。"""
        result = InsightSeedResetResult(cleared=crud_insight.clear_user_data(self.db))
        invalidate_insight_stats_cache()
        return result

    def reset_samples(self) -> InsightSeedResetResult:
        cleared = crud_insight.clear_sample_data(self.db)
        cleared.update(crud_insight.clear_snapshot_data(self.db))
        cleared.update(crud_insight.clear_churn_labels(self.db))
        invalidate_insight_stats_cache()
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
        """每人一条样本（仅写样本表）。"""
        template_vectors = get_seed_template_vectors(show_progress=True)
        inserted = 0
        for offset in range(0, count, SAMPLE_BATCH_SIZE):
            batch_size = min(SAMPLE_BATCH_SIZE, count - offset)
            people = [generate_profile_row() for _ in range(batch_size)]
            rows = []
            for person in people:
                survey = build_survey_row()
                complaint = build_complaint_row(_PAIR_RANDOM.choice(pairs), person)
                sat = float(survey["satisfaction_score"])
                srv = survey["survey_category_scores"].get("customer_service", sat)
                sat_net = max(1, min(5, int(round(sat))))
                sat_srv = max(1, min(5, int(round(float(srv)))))
                template_key = complaint.pop("_template_key")
                rows.append(
                    {
                        **survey,
                        **complaint,
                        "satisfaction_net": sat_net,
                        "satisfaction_srv": sat_srv,
                        "complaint_vector": vector_for_seed_template(template_key, template_vectors),
                    }
                )
            inserted += crud_insight.bulk_insert_complaint_touchpoints(self.db, rows)
            logger.info("Insight 样本注入进度 %s/%s", min(offset + batch_size, count), count)
        return inserted
