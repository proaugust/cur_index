"""决策中心：高风险清单、WHAT-IF 仿真、模型状态。"""

from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.insight import CfgSimulationWeight, DimUserProfile, DimUserProfileSnapshot
from app.schemas.insight import (
    InsightDecisionDashboard,
    InsightDecisionRecommendation,
    InsightDecisionSimulateResult,
    InsightModelTrainResult,
    InsightSimulationWeightRead,
)
from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
from app.services.modules.insight.ml.lgbm_scorer import LgbmRiskScorer
from app.services.modules.insight.ml.mock_scorer import mock_score, risk_level
from app.services.modules.insight.ml.model_registry import InsightModelRegistry
from app.services.modules.insight.ml.trainer import InsightModelTrainer


class InsightDecisionService:
    def __init__(self, db: Session):
        self.db = db
        self.registry = InsightModelRegistry()

    def dashboard(self) -> InsightDecisionDashboard:
        latest_date = self.db.query(func.max(DimUserProfileSnapshot.snapshot_date)).scalar()
        high_risk = 0
        total_snapshots = 0
        if latest_date:
            total_snapshots = (
                self.db.query(func.count(DimUserProfileSnapshot.user_id))
                .filter(DimUserProfileSnapshot.snapshot_date == latest_date)
                .scalar()
                or 0
            )
            high_risk = (
                self.db.query(func.count(DimUserProfileSnapshot.user_id))
                .filter(
                    DimUserProfileSnapshot.snapshot_date == latest_date,
                    DimUserProfileSnapshot.churn_risk_level == "high",
                )
                .scalar()
                or 0
            )
        weights = [InsightSimulationWeightRead.model_validate(row) for row in self.db.query(CfgSimulationWeight).all()]
        metrics = self._load_train_metrics()
        return InsightDecisionDashboard(
            model_version=self.registry.resolve_version(),
            has_trained_model=self.registry.has_model(),
            latest_snapshot_date=latest_date,
            snapshot_total=int(total_snapshots),
            high_risk_total=int(high_risk),
            simulation_weights=weights,
            **metrics,
        )

    def recommendations(self, *, limit: int = 20) -> list[InsightDecisionRecommendation]:
        latest_date = self.db.query(func.max(DimUserProfileSnapshot.snapshot_date)).scalar()
        if not latest_date:
            return []
        rows = (
            self.db.query(DimUserProfileSnapshot, DimUserProfile.name)
            .join(DimUserProfile, DimUserProfile.user_id == DimUserProfileSnapshot.user_id)
            .filter(
                DimUserProfileSnapshot.snapshot_date == latest_date,
                DimUserProfileSnapshot.churn_risk_level == "high",
            )
            .order_by(DimUserProfileSnapshot.risk_score.desc())
            .limit(limit)
            .all()
        )
        return [
            InsightDecisionRecommendation(
                user_id=snapshot.user_id,
                name=name,
                risk_score=snapshot.risk_score,
                churn_risk_level=snapshot.churn_risk_level,
                tags=snapshot.tags or [],
                top_shap=_top_shap(snapshot.shap_values),
                suggested_action=_suggest_action(snapshot.shap_values),
            )
            for snapshot, name in rows
        ]

    def simulate(self, user_id: str, adjustments: dict[str, float]) -> InsightDecisionSimulateResult:
        user = self.db.get(DimUserProfile, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        builder = InsightFeatureBuilder(self.db)
        feature = builder.build_batch([user])[user_id]
        baseline = self._predict_one(user, feature)
        adjusted = self._apply_adjustments(feature, adjustments)
        scenario = self._predict_one(user, adjusted)
        delta = scenario - baseline
        return InsightDecisionSimulateResult(
            user_id=user_id,
            baseline_risk=baseline,
            scenario_risk=scenario,
            delta_risk=delta.quantize(Decimal("0.0001")),
            baseline_level=risk_level(baseline),
            scenario_level=risk_level(scenario),
            adjustments=adjustments,
        )

    def train_model(self) -> InsightModelTrainResult:
        result = InsightModelTrainer(self.db).train()
        self.db.commit()
        msg = "训练完成（弱标签 holdout，非真实流失准确率）"
        if result.val_accuracy is not None:
            msg = f"{msg}；Accuracy={result.val_accuracy:.2%}"
            if result.val_auc is not None:
                msg = f"{msg}，AUC={result.val_auc:.4f}"
        return InsightModelTrainResult(
            model_version=result.model_version,
            message=msg,
            val_auc=result.val_auc,
            val_accuracy=result.val_accuracy,
            train_rows=result.train_rows,
            val_rows=result.val_rows,
            label_source=result.label_source,
        )

    def _load_train_metrics(self) -> dict:
        if not self.registry.has_model():
            return {}
        art = self.registry.load_artifacts()
        return {
            "val_auc": art.val_auc,
            "val_accuracy": art.val_accuracy,
            "train_rows": art.train_rows,
            "val_rows": art.val_rows,
            "label_source": art.label_source,
        }

    def _predict_one(self, user: DimUserProfile, feature) -> Decimal:
        if self.registry.has_model():
            scorer = LgbmRiskScorer(self.registry)
            return scorer.predict_batch({user.user_id: feature})[user.user_id]
        return mock_score(user, feature)

    @staticmethod
    def _apply_adjustments(feature, adjustments: dict[str, float]):
        from app.services.modules.insight.ml.feature_labels import FEATURE_NAMES
        from app.services.modules.insight.ml.types import UserFeatureRow

        values = list(feature.values)
        for key, value in adjustments.items():
            if key not in FEATURE_NAMES:
                continue
            values[FEATURE_NAMES.index(key)] = float(value)
        return UserFeatureRow(
            user_id=feature.user_id,
            has_sample=feature.has_sample,
            complaint_cnt=feature.complaint_cnt,
            avg_satisfaction=feature.avg_satisfaction,
            dominant_type=feature.dominant_type,
            values=values,
        )


def _top_shap(shap_values: dict | None) -> dict[str, float]:
    if not shap_values:
        return {}
    pairs = sorted(shap_values.items(), key=lambda item: abs(float(item[1])), reverse=True)[:5]
    return {str(key): float(value) for key, value in pairs}


def _suggest_action(shap_values: dict | None) -> str:
    if not shap_values:
        return "建议回访并收集问卷样本"
    top_name = max(shap_values.items(), key=lambda item: abs(float(item[1])))[0]
    if "投诉" in top_name or "网络" in top_name:
        return "优先安排网络质量专项排查与工程师上门"
    if "满意度" in top_name or "服务" in top_name or "客服" in top_name:
        return "指派客户经理回访，提升服务满意度"
    if "资费" in top_name or "账单" in top_name or "价格" in top_name:
        return "提供资费解释或套餐优化方案"
    if "套餐" in top_name:
        return "评估套餐匹配度，推荐权益升级或降费方案"
    return "针对首要归因特征制定挽留方案"
