"""Insight M2：单客画像点查 + 热点缓存。"""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.insight import DimUserProfile, DimUserProfileSnapshot, FactComplaintSample
from app.schemas.insight import (
    InsightComplaintRead,
    InsightComplaintSampleRead,
    InsightProfileCacheMeta,
    InsightProfileSnapshotRead,
    InsightProfileStats,
    InsightTouchpointRead,
    InsightUserProfileRead,
    InsightUserProfileResponse,
)
from app.services.modules.insight.constants import (
    PROFILE_HOT_COMPLAINT_MIN,
    PROFILE_HOT_RISK_THRESHOLD,
    PROFILE_HOT_VIP_LEVELS,
    PROFILE_RECENT_COMPLAINT_LIMIT,
    PROFILE_RECENT_TOUCHPOINT_LIMIT,
)
from app.services.modules.insight.profile_cache import get_cached_profile, set_cached_profile


class InsightProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_profile(self, user_id: str) -> InsightUserProfileResponse:
        cached = get_cached_profile(user_id)
        if cached is not None:
            return cached

        profile = self._load_from_db(user_id)
        if self._is_hot(profile):
            hot_profile = profile.model_copy(
                update={"cache": InsightProfileCacheMeta(hit=False, hot=True, source="db", ttl_seconds=settings.insight_profile_cache_ttl)}
            )
            set_cached_profile(user_id, hot_profile)
            return hot_profile
        return profile

    def _load_from_db(self, user_id: str) -> InsightUserProfileResponse:
        row = self.db.get(DimUserProfile, user_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        stats = self._load_stats(user_id)
        recent_complaints = self._load_recent_complaints(user_id, row.region)
        recent_samples = self._load_recent_samples(user_id)
        snapshot = self._load_latest_snapshot(user_id)
        profile_read = InsightUserProfileRead.model_validate(row)
        if snapshot:
            profile_read = profile_read.model_copy(
                update={
                    "risk_score": snapshot.risk_score,
                    "risk_level": snapshot.churn_risk_level,
                    "tags": snapshot.tags,
                    "shap_values": snapshot.shap_values,
                }
            )
        hot = self._is_hot_values(stats, row.vip_level, profile_read.risk_score)

        return InsightUserProfileResponse(
            profile=profile_read,
            stats=stats,
            recent_complaints=recent_complaints,
            recent_touchpoints=recent_samples,
            recent_samples=recent_samples,
            snapshot=snapshot,
            cache=InsightProfileCacheMeta(hit=False, hot=hot, source="db"),
        )

    def _load_latest_snapshot(self, user_id: str) -> InsightProfileSnapshotRead | None:
        row = (
            self.db.query(DimUserProfileSnapshot)
            .filter_by(user_id=user_id)
            .order_by(DimUserProfileSnapshot.snapshot_date.desc())
            .first()
        )
        return InsightProfileSnapshotRead.model_validate(row) if row else None

    def _load_stats(self, user_id: str) -> InsightProfileStats:
        complaint_total = (
            self.db.query(func.count(FactComplaintSample.complaint_id))
            .filter(FactComplaintSample.user_id == user_id)
            .filter(FactComplaintSample.complaint_id.isnot(None))
            .scalar()
            or 0
        )
        sample_total = self.db.query(func.count(FactComplaintSample.sample_id)).filter_by(user_id=user_id).scalar() or 0
        latest_complaint = (
            self.db.query(func.max(FactComplaintSample.sample_time))
            .filter(FactComplaintSample.user_id == user_id)
            .filter(FactComplaintSample.complaint_id.isnot(None))
            .scalar()
        )
        latest_sample = self.db.query(func.max(FactComplaintSample.sample_time)).filter_by(user_id=user_id).scalar()
        latest_date = self.db.query(func.max(FactComplaintSample.record_date)).filter_by(user_id=user_id).scalar()
        return InsightProfileStats(
            complaint_total=int(complaint_total),
            touchpoint_total=int(sample_total),
            sample_total=int(sample_total),
            latest_complaint_time=latest_complaint,
            latest_touchpoint_date=latest_date,
            latest_sample_time=latest_sample,
        )

    def _load_recent_complaints(self, user_id: str, region: str) -> list[InsightComplaintRead]:
        rows = (
            self.db.query(FactComplaintSample)
            .filter_by(user_id=user_id)
            .filter(FactComplaintSample.complaint_id.isnot(None))
            .order_by(FactComplaintSample.sample_time.desc(), FactComplaintSample.complaint_id.desc())
            .limit(PROFILE_RECENT_COMPLAINT_LIMIT)
            .all()
        )
        return [
            InsightComplaintRead.model_validate(row).model_copy(update={"region": region, "complaint_vector": None})
            for row in rows
        ]

    def _load_recent_samples(self, user_id: str) -> list[InsightTouchpointRead]:
        rows = (
            self.db.query(FactComplaintSample)
            .filter_by(user_id=user_id)
            .order_by(FactComplaintSample.record_date.desc(), FactComplaintSample.sample_id.desc())
            .limit(PROFILE_RECENT_TOUCHPOINT_LIMIT)
            .all()
        )
        return [
            InsightComplaintSampleRead.model_validate(row).model_copy(update={"complaint_vector": None})
            for row in rows
        ]

    def _is_hot(self, profile: InsightUserProfileResponse) -> bool:
        return self._is_hot_values(profile.stats, profile.profile.vip_level, profile.profile.risk_score)

    @staticmethod
    def _is_hot_values(stats: InsightProfileStats, vip_level: str, risk_score) -> bool:
        if risk_score is not None and float(risk_score) >= PROFILE_HOT_RISK_THRESHOLD:
            return True
        if stats.complaint_total >= PROFILE_HOT_COMPLAINT_MIN and vip_level in PROFILE_HOT_VIP_LEVELS:
            return True
        return stats.complaint_total >= PROFILE_HOT_COMPLAINT_MIN + 2
