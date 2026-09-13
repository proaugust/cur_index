"""样本满意度（真值）vs 客户预测满意度：相关 / MAE / RMSE。"""

from __future__ import annotations

import math
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, FactComplaintSample
from app.schemas.insight import InsightSatisfactionEvalItem, InsightSatisfactionEvalResponse


def risk_to_pred_satisfaction(risk_score: float | Decimal) -> float:
    """风险 0→满意度约 5，风险 1→约 1。"""
    risk = max(0.0, min(1.0, float(risk_score)))
    return round(1.0 + 4.0 * (1.0 - risk), 2)


def evaluate_satisfaction(db: Session, *, limit_examples: int = 20) -> InsightSatisfactionEvalResponse:
    sample_rows = (
        db.query(
            FactComplaintSample.user_id,
            func.avg(FactComplaintSample.satisfaction_score).label("avg_sat"),
        )
        .group_by(FactComplaintSample.user_id)
        .all()
    )
    if not sample_rows:
        return InsightSatisfactionEvalResponse(n=0, message="无样本满意度数据，请先注入样本并完成风险预测")

    truth = {uid: float(avg) for uid, avg in sample_rows if avg is not None}
    profiles = (
        db.query(DimUserProfile.user_id, DimUserProfile.pred_satisfaction, DimUserProfile.sample_satisfaction)
        .filter(DimUserProfile.user_id.in_(list(truth.keys())))
        .all()
    )
    pairs: list[tuple[str, float, float]] = []
    for user_id, pred, sample_sat in profiles:
        pred_v = float(pred) if pred is not None else None
        truth_v = float(sample_sat) if sample_sat is not None else truth.get(user_id)
        if pred_v is None or truth_v is None:
            continue
        pairs.append((user_id, truth_v, pred_v))

    if not pairs:
        return InsightSatisfactionEvalResponse(
            n=0,
            message="有样本但客户侧尚无 pred_satisfaction，请先跑风险快照/批处理写回预测",
        )

    n = len(pairs)
    errors = [abs(t - p) for _, t, p in pairs]
    sq_errors = [(t - p) ** 2 for _, t, p in pairs]
    mae = sum(errors) / n
    rmse = math.sqrt(sum(sq_errors) / n)
    mean_t = sum(t for _, t, _ in pairs) / n
    mean_p = sum(p for _, _, p in pairs) / n
    num = sum((t - mean_t) * (p - mean_p) for _, t, p in pairs)
    den_t = math.sqrt(sum((t - mean_t) ** 2 for _, t, _ in pairs))
    den_p = math.sqrt(sum((p - mean_p) ** 2 for _, _, p in pairs))
    pearson = (num / (den_t * den_p)) if den_t > 0 and den_p > 0 else None

    ranked = sorted(pairs, key=lambda item: abs(item[1] - item[2]), reverse=True)[:limit_examples]
    examples = [
        InsightSatisfactionEvalItem(
            user_id=uid,
            sample_satisfaction=round(truth_v, 2),
            pred_satisfaction=round(pred_v, 2),
            abs_error=round(abs(truth_v - pred_v), 2),
        )
        for uid, truth_v, pred_v in ranked
    ]
    return InsightSatisfactionEvalResponse(
        n=n,
        mae=round(mae, 4),
        rmse=round(rmse, 4),
        pearson=round(pearson, 4) if pearson is not None else None,
        examples=examples,
        message="样本真值满意度 vs 客户预测满意度（由风险分映射）",
    )
