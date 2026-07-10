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


class InsightSnapshotWriter:
    def __init__(self, db: Session):
        self.db = db

    def write(self, snapshot_date: date, predictions: list[RiskPrediction]) -> int:
        self.db.execute(delete(DimUserProfileSnapshot).where(DimUserProfileSnapshot.snapshot_date == snapshot_date))
        self.db.flush()

        rows = [
            {
                "snapshot_date": snapshot_date,
                "user_id": item["user_id"],
                "region_l1": item["region_l1"],
                "region_l2": item["region_l2"],
                "age_group": item["age_group"],
                "plan_id": item["plan_id"],
                "vip_level": item["vip_level"],
                "churn_risk_level": item["churn_risk_level"],
                "activity_trend": item["activity_trend"],
                "risk_score": item["risk_score"],
                "tags": item["tags"],
                "shap_values": item["shap_values"],
            }
            for item in predictions
        ]
        profile_rows = [
            {
                "user_id": item["user_id"],
                "risk_score": item["risk_score"],
                "risk_level": item["churn_risk_level"],
                "tags": item["tags"],
                "shap_values": item["shap_values"],
            }
            for item in predictions
        ]

        batch = SNAPSHOT_WRITE_BATCH_SIZE
        for chunk in _chunks(rows, batch):
            self.db.bulk_insert_mappings(DimUserProfileSnapshot, chunk)
            self.db.flush()
        for chunk in _chunks(profile_rows, batch):
            self.db.bulk_update_mappings(DimUserProfile, chunk)
            self.db.flush()

        if rows:
            clear_all_profile_cache()
        logger.info("快照落库完成 date=%s rows=%s batch=%s", snapshot_date, len(rows), batch)
        return len(rows)
