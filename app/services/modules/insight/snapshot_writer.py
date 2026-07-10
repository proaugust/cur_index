"""Insight 快照落库：将 AI 产出写入 insight_user_profile_snapshot，并回写主表风险字段。"""

import logging
from datetime import date

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, DimUserProfileSnapshot
from app.services.modules.insight.ai_risk_engine import RiskPrediction
from app.services.modules.insight.profile_cache import clear_all_profile_cache

logger = logging.getLogger(__name__)


class InsightSnapshotWriter:
    def __init__(self, db: Session):
        self.db = db

    def write(self, snapshot_date: date, predictions: list[RiskPrediction]) -> int:
        self.db.execute(delete(DimUserProfileSnapshot).where(DimUserProfileSnapshot.snapshot_date == snapshot_date))
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
        if rows:
            self.db.bulk_insert_mappings(DimUserProfileSnapshot, rows)
            # 主表风险字段供列表/兼容读取；与最新快照对齐
            self.db.bulk_update_mappings(
                DimUserProfile,
                [
                    {
                        "user_id": item["user_id"],
                        "risk_score": item["risk_score"],
                        "risk_level": item["churn_risk_level"],
                        "tags": item["tags"],
                        "shap_values": item["shap_values"],
                    }
                    for item in predictions
                ],
            )
            clear_all_profile_cache()
        logger.info("快照落库完成 date=%s rows=%s", snapshot_date, len(rows))
        return len(rows)
