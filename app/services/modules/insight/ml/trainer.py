"""离线训练 LightGBM + K-Means，并同步仿真权重。"""

import logging
from dataclasses import dataclass
from datetime import date

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models.insight import CfgSimulationWeight, DimUserProfile
from app.services.modules.insight.constants import LABEL_SOURCE_REAL
from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
from app.services.modules.insight.ml.label_loader import LabeledTrainRow, collect_train_rows
from app.services.modules.insight.ml.model_registry import InsightModelArtifacts, InsightModelRegistry
from app.services.modules.insight.ml.shap_utils import normalize_shap_dict

logger = logging.getLogger(__name__)
_MIN_TRAIN_ROWS = 30
_HOLDOUT_RATIO = 0.2


@dataclass
class InsightTrainResult:
    model_version: str
    val_auc: float | None
    val_accuracy: float | None
    train_rows: int
    val_rows: int
    label_source: str


class InsightModelTrainer:
    def __init__(self, db: Session):
        self.db = db
        self.registry = InsightModelRegistry()

    def train(self, users: list[DimUserProfile] | None = None) -> InsightTrainResult:
        users = users or self.db.query(DimUserProfile).all()
        if not users:
            raise ValueError("无用户主数据，无法训练")
        train_rows, label_source = collect_train_rows(self.db, users)
        if len(train_rows) < _MIN_TRAIN_ROWS:
            raise ValueError(
                f"有标签样本不足 {len(train_rows)} < {_MIN_TRAIN_ROWS}。"
                "请重新注入样本（生成合成流失标签）或导入 CSV 标签后重试"
            )

        names = InsightFeatureBuilder.feature_names()
        x_all = np.array([row.values for row in train_rows], dtype=np.float32)
        y_all = np.array([row.label for row in train_rows], dtype=np.int32)
        as_of = [row.as_of_date for row in train_rows]
        metrics = self._eval_metrics(x_all, y_all, as_of, label_source)

        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(x_all)
        booster = self._fit_lgbm(x_scaled, y_all)
        kmeans, cluster_shap = self._fit_clusters(train_rows, names, scaler, booster)
        version = f"lgbm-v1.0-{date.today().isoformat()}"
        artifacts = InsightModelArtifacts(
            version=version,
            feature_names=names,
            scaler=scaler,
            kmeans=kmeans,
            cluster_shap=cluster_shap,
            val_auc=metrics["val_auc"],
            val_accuracy=metrics["val_accuracy"],
            train_rows=metrics["train_rows"],
            val_rows=metrics["val_rows"],
            label_source=label_source,
        )
        self.registry.save(booster, artifacts)
        self._sync_simulation_weights(booster, names)
        logger.info(
            "Insight 训练完成 version=%s source=%s rows=%s val_auc=%s val_acc=%s",
            version,
            label_source,
            len(train_rows),
            metrics["val_auc"],
            metrics["val_accuracy"],
        )
        return InsightTrainResult(
            model_version=version,
            val_auc=metrics["val_auc"],
            val_accuracy=metrics["val_accuracy"],
            train_rows=metrics["train_rows"],
            val_rows=metrics["val_rows"],
            label_source=label_source,
        )

    @classmethod
    def _eval_metrics(
        cls,
        x_all: np.ndarray,
        y_all: np.ndarray,
        as_of: list[date | None],
        label_source: str,
    ) -> dict:
        empty = {"val_auc": None, "val_accuracy": None, "train_rows": int(len(x_all)), "val_rows": 0}
        if len(x_all) < _MIN_TRAIN_ROWS or len(np.unique(y_all)) < 2:
            return empty
        if label_source == LABEL_SOURCE_REAL and any(d is not None for d in as_of):
            return cls._time_split_metrics(x_all, y_all, as_of)
        return cls._random_holdout_metrics(x_all, y_all)

    @classmethod
    def _time_split_metrics(cls, x_all: np.ndarray, y_all: np.ndarray, as_of: list[date | None]) -> dict:
        dates = sorted({d for d in as_of if d is not None})
        if len(dates) < 2:
            return cls._random_holdout_metrics(x_all, y_all)
        cut = max(1, int(len(dates) * (1 - _HOLDOUT_RATIO)))
        val_dates = set(dates[cut:])
        mask = np.array([d in val_dates for d in as_of], dtype=bool)
        if not mask.any() or mask.all() or len(np.unique(y_all[~mask])) < 2:
            return cls._random_holdout_metrics(x_all, y_all)
        return cls._score_split(x_all[~mask], y_all[~mask], x_all[mask], y_all[mask])

    @classmethod
    def _random_holdout_metrics(cls, x_all: np.ndarray, y_all: np.ndarray) -> dict:
        stratify = y_all if int(np.min(np.bincount(y_all))) >= 2 else None
        x_tr, x_va, y_tr, y_va = train_test_split(
            x_all, y_all, test_size=_HOLDOUT_RATIO, random_state=42, stratify=stratify
        )
        return cls._score_split(x_tr, y_tr, x_va, y_va)

    @classmethod
    def _score_split(cls, x_tr, y_tr, x_va, y_va) -> dict:
        scaler = StandardScaler()
        booster = cls._fit_lgbm(scaler.fit_transform(x_tr), y_tr)
        probs = booster.predict(scaler.transform(x_va))
        preds = (probs >= 0.5).astype(np.int32)
        auc = None
        if len(np.unique(y_va)) >= 2:
            auc = round(float(roc_auc_score(y_va, probs)), 4)
        return {
            "val_auc": auc,
            "val_accuracy": round(float(accuracy_score(y_va, preds)), 4),
            "train_rows": int(len(x_tr)),
            "val_rows": int(len(x_va)),
        }

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

    def _fit_clusters(self, train_rows: list[LabeledTrainRow], names, scaler, booster):
        x = np.array([row.values for row in train_rows], dtype=np.float32)
        x_scaled = scaler.transform(x)
        cluster_count = max(3, min(12, len(train_rows) // 40))
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
