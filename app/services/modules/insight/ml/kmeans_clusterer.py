"""K-Means 沉默客户外推：最近簇 SHAP + 标签（不改写 LGBM 分数）。"""

from collections import Counter, defaultdict

import numpy as np

from app.models.insight import DimUserProfile
from app.services.modules.insight.ml.lgbm_scorer import LgbmRiskScorer
from app.services.modules.insight.ml.types import RiskPrediction, UserFeatureRow


def apply_kmeans_tags(
    scorer: LgbmRiskScorer,
    users: list[DimUserProfile],
    features: dict[str, UserFeatureRow],
    predictions: list[RiskPrediction],
    shap_map: dict[str, dict[str, float]],
) -> None:
    del users, shap_map  # 接口保留，当前仅用 features + predictions
    artifacts = scorer.artifacts
    if artifacts.kmeans is None or not predictions:
        return

    user_ids = [row["user_id"] for row in predictions]
    matrix = np.array([features[uid].values for uid in user_ids], dtype=np.float32)
    scaled = artifacts.scaler.transform(matrix)
    cluster_ids = artifacts.kmeans.predict(scaled).tolist()
    user_cluster_map = dict(zip(user_ids, cluster_ids))

    cluster_tags: dict[int, list[str]] = defaultdict(list)
    for row in predictions:
        uid = row["user_id"]
        if not features[uid].has_sample or row["churn_risk_level"] != "high":
            continue
        cluster_tags[user_cluster_map[uid]].extend(row["tags"])

    cluster_mode = {
        cid: Counter(tags).most_common(1)[0][0] for cid, tags in cluster_tags.items() if tags
    }

    for row in predictions:
        uid = row["user_id"]
        if features[uid].has_sample:
            continue
        cluster_id = user_cluster_map[uid]
        mode_tag = cluster_mode.get(cluster_id)
        if mode_tag:
            row["tags"] = [*row["tags"], f"沉默客户·{mode_tag}"]
        cluster_shap = artifacts.cluster_shap.get(cluster_id)
        if cluster_shap:
            row["shap_values"] = dict(cluster_shap)
