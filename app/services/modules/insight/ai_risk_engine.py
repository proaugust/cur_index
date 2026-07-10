"""Insight AI 风险引擎：LightGBM + SHAP + K-Means（无模型时 fallback mock）。"""

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.insight import DimUserProfile
from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
from app.services.modules.insight.ml.kmeans_clusterer import apply_kmeans_tags
from app.services.modules.insight.ml.lgbm_scorer import LgbmRiskScorer
from app.services.modules.insight.ml.mock_scorer import mock_score, mock_shap, risk_level
from app.services.modules.insight.ml.model_registry import InsightModelRegistry
from app.services.modules.insight.ml.shap_explainer import explain_batch
from app.services.modules.insight.ml.trainer import InsightModelTrainer
from app.services.modules.insight.ml.types import RiskPrediction, UserFeatureRow

logger = logging.getLogger(__name__)

# 兼容旧 import
MOCK_MODEL_VERSION = "mock-v1.0"

__all__ = ["InsightAiRiskEngine", "RiskPrediction", "MOCK_MODEL_VERSION", "risk_level"]


class InsightAiRiskEngine:
    def __init__(self) -> None:
        self.registry = InsightModelRegistry()

    @property
    def model_version(self) -> str:
        return self.registry.resolve_version()

    def run(
        self,
        db: Session,
        users: list[DimUserProfile],
        *,
        dampen: Decimal = Decimal("0"),
    ) -> list[RiskPrediction]:
        features = InsightFeatureBuilder(db).build_batch(users)
        self._ensure_model(db, users)
        if self.registry.has_model():
            predictions = self._run_lgbm(users, features, dampen=dampen)
        else:
            predictions = self._run_mock(users, features, dampen=dampen)
        logger.info("AI 风险引擎完成 users=%s model=%s", len(predictions), self.model_version)
        return predictions

    def _ensure_model(self, db: Session, users: list[DimUserProfile]) -> None:
        if self.registry.has_model() or not settings.insight_auto_train:
            return
        try:
            InsightModelTrainer(db).train(users)
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("自动训练失败，将使用 mock 引擎: %s", exc)

    def _run_lgbm(
        self,
        users: list[DimUserProfile],
        features: dict[str, UserFeatureRow],
        *,
        dampen: Decimal,
    ) -> list[RiskPrediction]:
        scorer = LgbmRiskScorer(self.registry)
        scores = scorer.predict_batch(features, dampen=float(dampen))
        sample_ids = [user_id for user_id, row in features.items() if row.has_sample]
        score_float = {user_id: float(score) for user_id, score in scores.items()}
        shap_map = explain_batch(scorer, features, sample_ids, score_float)
        predictions = [
            self._build_row(user, features[user.user_id], scores[user.user_id], shap_map.get(user.user_id))
            for user in users
        ]
        apply_kmeans_tags(scorer, users, features, predictions, shap_map)
        return predictions

    def _run_mock(
        self,
        users: list[DimUserProfile],
        features: dict[str, UserFeatureRow],
        *,
        dampen: Decimal,
    ) -> list[RiskPrediction]:
        predictions = []
        for user in users:
            feature = features[user.user_id]
            score = mock_score(user, feature, dampen=dampen)
            predictions.append(self._build_row(user, feature, score, mock_shap(user, feature, score)))
        self._apply_rule_tags(predictions, features)
        return predictions

    @staticmethod
    def _build_row(
        user: DimUserProfile,
        feature: UserFeatureRow,
        score: Decimal,
        shap_values: dict[str, float] | None,
    ) -> RiskPrediction:
        return {
            "user_id": user.user_id,
            "region_l1": user.region_l1,
            "region_l2": user.region_l2,
            "age_group": user.age_group,
            "plan_id": user.plan_id,
            "vip_level": user.vip_level,
            "churn_risk_level": risk_level(score),
            "activity_trend": _activity_trend(feature),
            "risk_score": score,
            "tags": _direct_tags(user, feature),
            "shap_values": shap_values or {},
        }

    @staticmethod
    def _apply_rule_tags(predictions: list[RiskPrediction], features: dict[str, UserFeatureRow]) -> None:
        cluster_tags: dict[str, list[str]] = {}
        for row in predictions:
            feature = features[row["user_id"]]
            if feature.has_sample and row["churn_risk_level"] == "high":
                key = f"{row['age_group']}|{row['plan_id']}|{row['region_l1']}"
                cluster_tags.setdefault(key, []).extend(row["tags"])
        for row in predictions:
            feature = features[row["user_id"]]
            if feature.has_sample:
                continue
            key = f"{row['age_group']}|{row['plan_id']}|{row['region_l1']}"
            tags = cluster_tags.get(key, [])
            if tags:
                from collections import Counter

                mode = Counter(tags).most_common(1)[0][0]
                row["tags"] = [*row["tags"], f"沉默客户·{mode}"]


def _activity_trend(feature: UserFeatureRow) -> str:
    if feature.complaint_cnt >= 3:
        return "declining"
    if feature.complaint_cnt >= 1 or (feature.avg_satisfaction is not None and feature.avg_satisfaction <= 2.5):
        return "cooling"
    if feature.avg_satisfaction is not None and feature.avg_satisfaction >= 4.0:
        return "rising"
    return "stable"


def _direct_tags(user: DimUserProfile, feature: UserFeatureRow) -> list[str]:
    tags: list[str] = []
    if feature.complaint_cnt >= 2:
        tags.append("多次投诉")
    if feature.avg_satisfaction is not None and feature.avg_satisfaction <= 2.5:
        tags.append("低满意度")
    if float(user.fee_drift_rate or 0) > 0.25:
        tags.append("资费敏感")
    if user.vip_level in ("金卡", "钻石"):
        tags.append("高价值客户")
    return tags
