"""Insight 快照落库：将 AI 产出写入 insight_user_profile_snapshot，并回写主表风险字段。"""

import logging
from datetime import date
from typing import Iterable, TypeVar

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, DimUserProfileSnapshot
from app.services.modules.insight.ai_risk_engine import RiskPrediction
from app.services.modules.insight.constants import SNAPSHOT_WRITE_BATCH_SIZE
from app.services.modules.insight.profile_cache import clear_all_profile_cache

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _chunks(items: list[T], size: int) -> Iterable[list[T]]:
    for offset in range(0, len(items), size):
        yield items[offset : offset + size]


def _jsonable_shap(shap_values: dict | None) -> dict[str, float]:
    if not shap_values:
        return {}
    return {str(key): float(value) for key, value in shap_values.items()}


class InsightSnapshotWriter:
    def __init__(self, db: Session):
        self.db = db

    def write(
        self,
        snapshot_date: date,
        predictions: list[RiskPrediction],
        *,
        replace_day: bool = True,
    ) -> int:
        self.db.expunge_all()
        if replace_day:
            self.db.execute(delete(DimUserProfileSnapshot).where(DimUserProfileSnapshot.snapshot_date == snapshot_date))
            self.db.commit()
        elif predictions:
            user_ids = [item["user_id"] for item in predictions]
            self.db.execute(
                delete(DimUserProfileSnapshot).where(
                    DimUserProfileSnapshot.snapshot_date == snapshot_date,
                    DimUserProfileSnapshot.user_id.in_(user_ids),
                )
            )
            self.db.commit()

        rows = [self._snapshot_row(snapshot_date, item) for item in predictions]
        profile_rows = [self._profile_row(item) for item in predictions]
        
        # 动态调整批次大小：如果数据量大，使用更大的批次并延迟 commit，减少网络往返
        if len(predictions) > 1000:
            batch = 2000
            for chunk in _chunks(rows, batch):
                self.db.bulk_insert_mappings(DimUserProfileSnapshot, chunk)
            self._update_profiles(profile_rows, batch, commit_per_batch=False)
            self.db.commit()
        else:
            batch = SNAPSHOT_WRITE_BATCH_SIZE
            for chunk in _chunks(rows, batch):
                self.db.bulk_insert_mappings(DimUserProfileSnapshot, chunk)
                self.db.commit()
            self._update_profiles(profile_rows, batch, commit_per_batch=True)

        if rows:
            clear_all_profile_cache()
        logger.info(
            "快照落库完成 date=%s rows=%s batch=%s replace_day=%s",
            snapshot_date,
            len(rows),
            batch,
            replace_day,
        )
        return len(rows)

    def _update_profiles(self, profile_rows: list[dict], batch: int, commit_per_batch: bool = True) -> None:
        if not profile_rows:
            return
        for chunk in _chunks(profile_rows, batch):
            self.db.bulk_update_mappings(DimUserProfile, chunk)
            if commit_per_batch:
                self.db.commit()

    @staticmethod
    def _snapshot_row(snapshot_date: date, item: RiskPrediction) -> dict:
        return {
            "snapshot_date": snapshot_date,
            "user_id": item["user_id"],
            "region_l1": item["region_l1"],
            "region_l2": item["region_l2"],
            "age_group": item["age_group"],
            "plan_id": item["plan_id"],
            "vip_level": item["vip_level"],
            "churn_risk_level": item["churn_risk_level"],
            "activity_trend": item["activity_trend"],
            "risk_score": float(item["risk_score"]),
            "tags": list(item["tags"] or []),
            "shap_values": _jsonable_shap(item["shap_values"]),
        }

    @staticmethod
    def _profile_row(item: RiskPrediction) -> dict:
        return {
            "user_id": item["user_id"],
            "risk_score": float(item["risk_score"]),
            "risk_level": item["churn_risk_level"],
            "tags": list(item["tags"] or []),
            "shap_values": _jsonable_shap(item["shap_values"]),
        }
