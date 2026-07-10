"""Insight ML 共享类型。"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TypedDict


class RiskPrediction(TypedDict):
    user_id: str
    region_l1: str
    region_l2: str
    age_group: str
    plan_id: str
    vip_level: str
    churn_risk_level: str
    activity_trend: str
    risk_score: Decimal
    tags: list[str]
    shap_values: dict[str, float]


@dataclass
class UserFeatureRow:
    user_id: str
    has_sample: bool
    complaint_cnt: int
    avg_satisfaction: float | None
    dominant_type: str | None
    values: list[float] = field(default_factory=list)

    def to_dict(self, names: list[str]) -> dict[str, float]:
        return {name: value for name, value in zip(names, self.values)}
