"""弱监督标签：造数环境无真实流失标签时的 proxy。"""

from app.models.insight import DimUserProfile
from app.services.modules.insight.ml.types import UserFeatureRow


def weak_label(user: DimUserProfile, feature: UserFeatureRow) -> int:
    if feature.complaint_cnt >= 2:
        return 1
    if feature.avg_satisfaction is not None and feature.avg_satisfaction <= 2.5:
        return 1
    if float(user.fee_drift_rate or 0) > 0.25:
        return 1
    loyalty = _feature_value(feature, "survey_loyalty_retention")
    if loyalty is not None and loyalty <= 2.0:
        return 1
    return 0


def _feature_value(feature: UserFeatureRow, name: str) -> float | None:
    from app.services.modules.insight.ml.feature_labels import FEATURE_NAMES

    if name not in FEATURE_NAMES:
        return None
    return feature.values[FEATURE_NAMES.index(name)]
