"""离线训练 LightGBM + K-Means，并同步仿真权重。"""

import logging
from datetime import date

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models.insight import CfgSimulationWeight, DimUserProfile
from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
from app.services.modules.insight.ml.shap_utils import normalize_shap_dict
from app.services.modules.insight.ml.model_registry import InsightModelArtifacts, InsightModelRegistry
from app.services.modules.insight.ml.types import UserFeatureRow
from app.services.modules.insight.ml.weak_label import weak_label

logger = logging.getLogger(__name__)
_MIN_TRAIN_ROWS = 30


class InsightModelTrainer:
    def __init__(self, db: Session):
        self.db = db
        self.registry = InsightModelRegistry()
        self.feature_builder = InsightFeatureBuilder(db)

    def train(self, users: list[DimUserProfile] | None = None) -> str:
        users = users or self.db.query(DimUserProfile).all()
        if not users:
            raise ValueError("无用户主数据，无法训练")
        features = self.feature_builder.build_batch(users)
        train_rows = self._collect_train_rows(users, features)
        if len(train_rows) < _MIN_TRAIN_ROWS:
            raise ValueError(f"有标签样本不足 {len(train_rows)} < {_MIN_TRAIN_ROWS}")

        names = InsightFeatureBuilder.feature_names()
        x_train = np.array([features[row.user_id].values for row in train_rows], dtype=np.float32)
        y_train = np.array([row.label for row in train_rows], dtype=np.int32)

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_train)
        booster = self._fit_lgbm(x_scaled, y_train)
        kmeans, cluster_shap = self._fit_clusters(train_rows, features, names, scaler, booster)
        version = f"lgbm-v1.0-{date.today().isoformat()}"
        artifacts = InsightModelArtifacts(
            version=version,
            feature_names=names,
            scaler=scaler,
            kmeans=kmeans,
            cluster_shap=cluster_shap,
        )
        self.registry.save(booster, artifacts)
        self._sync_simulation_weights(booster, names)
        logger.info("Insight 模型训练完成 version=%s train_rows=%s", version, len(train_rows))
        return version

    def _collect_train_rows(self, users: list[DimUserProfile], features: dict[str, UserFeatureRow]):
        rows = []
        for user in users:
            feature = features.get(user.user_id)
            if not feature or not feature.has_sample:
                continue
            rows.append(type("Row", (), {"user_id": user.user_id, "label": weak_label(user, feature)})())
        return rows

    @staticmethod
    def _fit_lgbm(x_train: np.ndarray, y_train: np.ndarray):
        import lightgbm as lgb

        train_set = lgb.Dataset(x_train, label=y_train)
        params = {
            "objective": "binary",
            "metric": "auc",
            "learning_rate": 0.08,
            "num_leaves": 31,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 1,
            "verbose": -1,
            "seed": 42,
        }
        return lgb.train(params, train_set, num_boost_round=120)

    def _fit_clusters(self, train_rows, features, names, scaler, booster):
        sample_ids = [row.user_id for row in train_rows]
        x = np.array([features[user_id].values for user_id in sample_ids], dtype=np.float32)
        x_scaled = scaler.transform(x)
        cluster_count = max(3, min(12, len(sample_ids) // 40))
        kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
        labels = kmeans.fit_predict(x_scaled)
        cluster_shap = self._mean_shap_by_cluster(booster, x_scaled, labels, names)
        return kmeans, cluster_shap

    @staticmethod
    def _mean_shap_by_cluster(booster, x_scaled: np.ndarray, labels: np.ndarray, names: list[str]) -> dict[int, dict[str, float]]:
        import shap

        explainer = shap.TreeExplainer(booster)
        shap_matrix = explainer.shap_values(x_scaled)
        if isinstance(shap_matrix, list):
            shap_matrix = shap_matrix[1]
        cluster_shap: dict[int, dict[str, float]] = {}
        probs = booster.predict(x_scaled)
        for cluster_id in sorted(set(labels.tolist())):
            mask = labels == cluster_id
            mean_row = shap_matrix[mask].mean(axis=0)
            mean_prob = float(np.median(probs[mask])) if mask.any() else 0.5
            cluster_shap[int(cluster_id)] = normalize_shap_dict(names, mean_row.tolist(), mean_prob)
        return cluster_shap

    def _sync_simulation_weights(self, booster, names: list[str]) -> None:
        importances = booster.feature_importance(importance_type="gain")
        pairs = sorted(zip(names, importances), key=lambda item: item[1], reverse=True)[:8]
        if not pairs:
            return
        max_gain = float(pairs[0][1]) or 1.0
        self.db.query(CfgSimulationWeight).delete()
        for name, gain in pairs:
            coef = -0.25 if name.startswith("survey_") or name.startswith("satisfaction") else 0.2
            if "complaint" in name or name.startswith("ctype_"):
                coef = 0.35
            self.db.add(
                CfgSimulationWeight(
                    feature_name=name,
                    base_importance=round(float(gain) / max_gain * 1000, 4),
                    impact_coefficient=coef,
                )
            )
        self.db.flush()
