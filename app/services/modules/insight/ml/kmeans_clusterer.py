"""K-Means 沉默客户外推：最近簇 SHAP + 标签。"""

from collections import Counter, defaultdict
from decimal import Decimal

import numpy as np

from app.models.insight import DimUserProfile
from app.services.modules.insight.ml.lgbm_scorer import LgbmRiskScorer
from app.services.modules.insight.ml.mock_scorer import risk_level
from app.services.modules.insight.ml.types import RiskPrediction, UserFeatureRow


def apply_kmeans_tags(
    scorer: LgbmRiskScorer,
    users: list[DimUserProfile],
    features: dict[str, UserFeatureRow],
    predictions: list[RiskPrediction],
    shap_map: dict[str, dict[str, float]],
) -> None:
    artifacts = scorer.artifacts
    if artifacts.kmeans is None or not predictions:
        return

    # 批量提取特征值并进行标准化和聚类预测
    user_ids = [row["user_id"] for row in predictions]
    matrix = np.array([features[uid].values for uid in user_ids], dtype=np.float32)
    scaled = artifacts.scaler.transform(matrix)
    cluster_ids = artifacts.kmeans.predict(scaled).tolist()
    user_cluster_map = dict(zip(user_ids, cluster_ids))

    cluster_tags: dict[int, list[str]] = defaultdict(list)
    cluster_scores: dict[int, list[float]] = defaultdict(list)

    for row in predictions:
        uid = row["user_id"]
        feature = features[uid]
        if not feature.has_sample or row["churn_risk_level"] != "high":
            continue
        cluster_id = user_cluster_map[uid]
        cluster_tags[cluster_id].extend(row["tags"])
        cluster_scores[cluster_id].append(float(row["risk_score"]))

    cluster_mode = {cid: Counter(tags).most_common(1)[0][0] for cid, tags in cluster_tags.items() if tags}
    cluster_risk = {cid: Decimal(str(round(np.median(values), 4))) for cid, values in cluster_scores.items() if values}

    for row in predictions:
        uid = row["user_id"]
        feature = features[uid]
        if feature.has_sample:
            continue
        cluster_id = user_cluster_map[uid]
        mode_tag = cluster_mode.get(cluster_id)
        if mode_tag:
            row["tags"] = [*row["tags"], f"沉默客户·{mode_tag}"]
        cluster_shap = artifacts.cluster_shap.get(cluster_id)
        if cluster_shap:
            row["shap_values"] = dict(cluster_shap)
        median = cluster_risk.get(cluster_id)
        if median is not None and float(row["risk_score"]) < float(median) * 0.85:
            row["risk_score"] = median
            row["churn_risk_level"] = risk_level(median)
