"""Insight AI 风险引擎：LightGBM + SHAP + K-Means（无模型时 fallback mock）。"""

import logging
from decimal import Decimal
from typing import Literal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.insight import DimUserProfile
from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
from app.services.modules.insight.ml.kmeans_clusterer import apply_kmeans_tags
from app.services.modules.insight.ml.lgbm_scorer import LgbmRiskScorer
from app.services.modules.insight.ml.mock_scorer import mock_score, mock_shap, risk_level
from app.services.modules.insight.ml.model_registry import InsightModelRegistry
from app.services.modules.insight.constants import SHAP_TOP_N_CAP
from app.services.modules.insight.ml.shap_explainer import explain_batch
from app.services.modules.insight.ml.trainer import InsightModelTrainer
from app.services.modules.insight.ml.types import RiskPrediction, UserFeatureRow

logger = logging.getLogger(__name__)

# 兼容旧 import
MOCK_MODEL_VERSION = "mock-v1.0"
ShapPolicy = Literal["all_sample", "high_only"]

__all__ = ["InsightAiRiskEngine", "RiskPrediction", "MOCK_MODEL_VERSION", "risk_level"]


class InsightAiRiskEngine:
    def __init__(self) -> None:
        self.registry = InsightModelRegistry()

    @property
    def model_version(self) -> str:
        return self.registry.resolve_version()

    def ensure_model(self, db: Session, users: list[DimUserProfile] | None = None) -> None:
        """批处理外层先调一次，避免每批重复触发自动训练。"""
        if self.registry.has_model() or not settings.insight_auto_train:
            return
        try:
            InsightModelTrainer(db).train(users)
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.warning("自动训练失败，将使用 mock 引擎: %s", exc)

    def run(
        self,
        db: Session,
        users: list[DimUserProfile],
        *,
        dampen: Decimal = Decimal("0"),
        shap_policy: ShapPolicy = "high_only",
        shap_top_n: int | None = SHAP_TOP_N_CAP,
        ensure_model: bool = True,
    ) -> list[RiskPrediction]:
        if ensure_model:
            self.ensure_model(db, users)
        features = InsightFeatureBuilder(db).build_batch(users)
        if self.registry.has_model():
            predictions = self._run_lgbm(
                users, features, dampen=dampen, shap_policy=shap_policy, shap_top_n=shap_top_n
            )
        else:
            predictions = self._run_mock(
                users, features, dampen=dampen, shap_policy=shap_policy, shap_top_n=shap_top_n
            )
        _downgrade_unexplained_high(predictions)
        logger.info(
            "AI 风险引擎完成 users=%s model=%s shap_policy=%s shap_top_n=%s",
            len(predictions),
            self.model_version,
            shap_policy,
            shap_top_n,
        )
        return predictions

    def _run_lgbm(
        self,
        users: list[DimUserProfile],
        features: dict[str, UserFeatureRow],
        *,
        dampen: Decimal,
        shap_policy: ShapPolicy,
        shap_top_n: int | None,
    ) -> list[RiskPrediction]:
        scorer = LgbmRiskScorer(self.registry)
        scores = scorer.predict_batch(features, dampen=float(dampen))
        sample_ids = [user_id for user_id, row in features.items() if row.has_sample]
        score_float = {user_id: float(score) for user_id, score in scores.items()}
        shap_ids = _select_shap_ids(sample_ids, scores, shap_policy, shap_top_n)
        logger.info(
            "SHAP 归因 %s/%s (policy=%s cap=%s)",
            len(shap_ids),
            len(sample_ids),
            shap_policy,
            shap_top_n,
        )
        shap_map = explain_batch(scorer, features, shap_ids, score_float)
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
        shap_policy: ShapPolicy,
        shap_top_n: int | None,
    ) -> list[RiskPrediction]:
        scored = [
            (user, features[user.user_id], mock_score(user, features[user.user_id], dampen=dampen))
            for user in users
        ]
        candidates = [
            (user.user_id, score)
            for user, _, score in scored
            if shap_policy == "all_sample" or risk_level(score) == "high"
        ]
        allow = {uid for uid, _ in _cap_by_score(candidates, shap_top_n)}
        predictions = [
            self._build_row(
                user,
                feature,
                score,
                mock_shap(user, feature, score) if user.user_id in allow else {},
            )
            for user, feature, score in scored
        ]
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


def _downgrade_unexplained_high(predictions: list[RiskPrediction]) -> None:
    """高风险必须有可展示归因；无 SHAP 则降为 medium 并打证据不足标签。"""
    for row in predictions:
        if row["churn_risk_level"] != "high":
            continue
        if row.get("shap_values"):
            continue
        row["churn_risk_level"] = "medium"
        if "证据不足" not in row["tags"]:
            row["tags"] = [*row["tags"], "证据不足"]


def _select_shap_ids(
    sample_ids: list[str],
    scores: dict[str, Decimal],
    shap_policy: ShapPolicy,
    shap_top_n: int | None,
) -> list[str]:
    if shap_policy == "all_sample":
        candidates = [(uid, scores[uid]) for uid in sample_ids]
    else:
        candidates = [(uid, scores[uid]) for uid in sample_ids if risk_level(scores[uid]) == "high"]
    return [uid for uid, _ in _cap_by_score(candidates, shap_top_n)]


def _cap_by_score(
    candidates: list[tuple[str, Decimal]],
    shap_top_n: int | None,
) -> list[tuple[str, Decimal]]:
    if shap_top_n is None or len(candidates) <= shap_top_n:
        return candidates
    return sorted(candidates, key=lambda item: item[1], reverse=True)[:shap_top_n]


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
