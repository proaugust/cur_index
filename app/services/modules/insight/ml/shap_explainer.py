"""SHAP TreeExplainer 批量归因。"""

import numpy as np

from app.services.modules.insight.ml.shap_utils import normalize_shap_dict
from app.services.modules.insight.ml.lgbm_scorer import LgbmRiskScorer
from app.services.modules.insight.ml.types import UserFeatureRow


def explain_batch(
    scorer: LgbmRiskScorer,
    features: dict[str, UserFeatureRow],
    user_ids: list[str],
    scores: dict[str, float],
    *,
    limit: int = 8,
) -> dict[str, dict[str, float]]:
    import shap

    if not user_ids:
        return {}
    artifacts = scorer.artifacts
    matrix = np.array([features[user_id].values for user_id in user_ids], dtype=np.float32)
    scaled = artifacts.scaler.transform(matrix)
    explainer = shap.TreeExplainer(scorer._booster)
    shap_matrix = explainer.shap_values(scaled)
    if isinstance(shap_matrix, list):
        shap_matrix = shap_matrix[1]
    result: dict[str, dict[str, float]] = {}
    for index, user_id in enumerate(user_ids):
        risk = float(scores.get(user_id, 0))
        result[user_id] = normalize_shap_dict(
            artifacts.feature_names,
            shap_matrix[index].tolist(),
            risk,
            limit=limit,
        )
    return result
