"""Mock 风险打分（无模型文件时 fallback）。"""

import hashlib
from decimal import Decimal

from app.models.insight import DimUserProfile
from app.services.modules.insight.ml.types import UserFeatureRow

_HIGH = Decimal("0.55")
_MEDIUM = Decimal("0.35")


def risk_level(score: Decimal) -> str:
    if score >= _HIGH:
        return "high"
    if score >= _MEDIUM:
        return "medium"
    return "low"


def mock_score(user: DimUserProfile, feature: UserFeatureRow, *, dampen: Decimal = Decimal("0")) -> Decimal:
    digest = hashlib.md5(user.user_id.encode()).hexdigest()[:8]
    base = Decimal("0.12") + Decimal(str(round(int(digest, 16) % 100 / 100 * 0.42, 4)))
    if feature.complaint_cnt:
        base += Decimal(str(min(0.40, feature.complaint_cnt * 0.11)))
    if feature.avg_satisfaction is not None:
        base += Decimal(str(max(0, (3.0 - feature.avg_satisfaction) * 0.10)))
    if float(user.fee_drift_rate or 0) > 0.2:
        base += Decimal("0.10")
    if user.vip_level == "普通":
        base += Decimal("0.06")
    if dampen:
        base = max(Decimal("0.05"), base - dampen)
    return min(Decimal("0.99"), base).quantize(Decimal("0.0001"))


def mock_shap(user: DimUserProfile, feature: UserFeatureRow, risk_score: Decimal) -> dict[str, float]:
    price = float(user.fee_drift_rate or 0) * 0.35
    service = max(0.0, (2.5 - (feature.avg_satisfaction or 3.0)) * 0.25) if feature.complaint_cnt else 0.05
    network = feature.complaint_cnt * 0.12
    plan = 0.08 if user.plan_id.endswith("元套餐") and float(user.monthly_fee or 0) >= 299 else 0.03
    if feature.dominant_type == "网络质量":
        network += 0.15
    elif feature.dominant_type == "客服":
        service += 0.15
    elif feature.dominant_type == "扣费":
        price += 0.15
    total = price + service + network + plan or 1.0
    scale = float(risk_score) / total
    return {
        "价格": round(price * scale, 4),
        "服务": round(service * scale, 4),
        "网络": round(network * scale, 4),
        "套餐": round(plan * scale, 4),
    }
