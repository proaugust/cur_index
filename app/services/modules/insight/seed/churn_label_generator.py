"""合成真实流失标签：概率采样，与 weak_label 硬规则解耦。"""

import math
import random
from datetime import date, timedelta

from app.models.insight import DimUserProfile
from app.services.modules.insight.constants import CHURN_HORIZON_DAYS
from app.services.modules.insight.ml.feature_labels import FEATURE_NAMES
from app.services.modules.insight.ml.types import UserFeatureRow

_RANDOM = random.Random(20260726)
# 多个观察日，便于训练走时间切分验证
_AS_OF_OFFSETS_DAYS = (300, 240, 180, 120, 60)


def default_as_of_dates(today: date | None = None) -> list[date]:
    ref = today or date.today()
    return [ref - timedelta(days=offset) for offset in _AS_OF_OFFSETS_DAYS]


def synthetic_churn_prob(user: DimUserProfile, feature: UserFeatureRow, rng: random.Random | None = None) -> float:
    """连续风险 logit + 高斯噪声 → 概率；同特征可得到不同标签。"""
    rng = rng or _RANDOM
    fee = float(user.fee_drift_rate or 0)
    sat = feature.avg_satisfaction if feature.avg_satisfaction is not None else 3.0
    loyalty = _feature_value(feature, "survey_loyalty_retention") or 3.0
    net = float(user.satisfaction_net or 3)
    srv = float(user.satisfaction_srv or 3)
    logit = (
        -1.4
        + 0.35 * float(feature.complaint_cnt)
        + 1.8 * fee
        + 0.55 * (3.0 - sat)
        + 0.35 * (3.0 - loyalty)
        + 0.25 * (3.0 - (net + srv) / 2.0)
        + rng.gauss(0.0, 1.1)
    )
    prob = 1.0 / (1.0 + math.exp(-logit))
    return min(0.92, max(0.04, prob))


def sample_churn_label(
    user: DimUserProfile,
    feature: UserFeatureRow,
    as_of: date,
    rng: random.Random | None = None,
) -> tuple[int, date | None]:
    rng = rng or _RANDOM
    churn = 1 if rng.random() < synthetic_churn_prob(user, feature, rng) else 0
    if not churn:
        return 0, None
    cancel = as_of + timedelta(days=rng.randint(1, CHURN_HORIZON_DAYS))
    return 1, cancel


def _feature_value(feature: UserFeatureRow, name: str) -> float | None:
    if name not in FEATURE_NAMES:
        return None
    return feature.values[FEATURE_NAMES.index(name)]
