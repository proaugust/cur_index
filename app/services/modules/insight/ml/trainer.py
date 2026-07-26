"""离线训练 LightGBM + K-Means，并同步仿真权重。"""

import logging
from dataclasses import dataclass
from datetime import date

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import accuracy_score, average_precision_score, roc_auc_score
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
_MAX_ROUNDS = 400
_EARLY_STOP = 40


@dataclass
class InsightTrainResult:
    model_version: str
    val_auc: float | None
    val_accuracy: float | None
    val_pr_auc: float | None
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
        booster, metrics = self._train_with_holdout(self._make_split(x_all, y_all, as_of, label_source))
        best_rounds = max(20, int(getattr(booster, "best_iteration", 0) or 120))
        return self._finalize(train_rows, names, x_all, y_all, best_rounds, metrics, label_source)

    def _finalize(self, train_rows, names, x_all, y_all, best_rounds, metrics, label_source) -> InsightTrainResult:
        scaler_full = StandardScaler()
        final = self._fit_lgbm(scaler_full.fit_transform(x_all), y_all, num_boost_round=best_rounds)
        kmeans, cluster_shap = self._fit_clusters(train_rows, names, scaler_full, final)
        version = f"lgbm-v1.1-{date.today().isoformat()}"
        artifacts = InsightModelArtifacts(
            version=version,
            feature_names=names,
            scaler=scaler_full,
            kmeans=kmeans,
            cluster_shap=cluster_shap,
            val_auc=metrics["val_auc"],
            val_accuracy=metrics["val_accuracy"],
            val_pr_auc=metrics["val_pr_auc"],
            train_rows=metrics["train_rows"],
            val_rows=metrics["val_rows"],
            label_source=label_source,
        )
        self.registry.save(final, artifacts)
        self._sync_simulation_weights(final, names)
        logger.info(
            "Insight 训练完成 version=%s source=%s auc=%s pr_auc=%s rounds=%s",
            version, label_source, metrics["val_auc"], metrics["val_pr_auc"], best_rounds,
        )
        return InsightTrainResult(
            model_version=version,
            val_auc=metrics["val_auc"],
            val_accuracy=metrics["val_accuracy"],
            val_pr_auc=metrics["val_pr_auc"],
            train_rows=metrics["train_rows"],
            val_rows=metrics["val_rows"],
            label_source=label_source,
        )

    def _train_with_holdout(self, split: dict) -> tuple:
        scaler = StandardScaler()
        x_tr = scaler.fit_transform(split["x_tr"])
        has_val = len(split["x_va"]) > 0
        x_va = scaler.transform(split["x_va"]) if has_val else split["x_va"]
        booster = self._fit_lgbm(
            x_tr,
            split["y_tr"],
            x_va=x_va if has_val else None,
            y_va=split["y_va"] if has_val else None,
        )
        return booster, self._score_booster(booster, x_va, split["y_va"], split["train_rows"])

    @classmethod
    def _make_split(cls, x_all, y_all, as_of, label_source: str) -> dict:
        empty = {
            "x_tr": x_all, "y_tr": y_all, "x_va": x_all[:0], "y_va": y_all[:0], "train_rows": len(x_all),
        }
        if len(x_all) < _MIN_TRAIN_ROWS or len(np.unique(y_all)) < 2:
            return empty
        if label_source == LABEL_SOURCE_REAL and any(d is not None for d in as_of):
            split = cls._time_split(x_all, y_all, as_of)
            if split is not None:
                return split
        return cls._random_split(x_all, y_all)

    @classmethod
    def _time_split(cls, x_all, y_all, as_of) -> dict | None:
        dates = sorted({d for d in as_of if d is not None})
        if len(dates) < 2:
            return None
        cut = max(1, int(len(dates) * (1 - _HOLDOUT_RATIO)))
        val_dates = set(dates[cut:])
        mask = np.array([d in val_dates for d in as_of], dtype=bool)
        if not mask.any() or mask.all() or len(np.unique(y_all[~mask])) < 2:
            return None
        return {
            "x_tr": x_all[~mask], "y_tr": y_all[~mask],
            "x_va": x_all[mask], "y_va": y_all[mask],
            "train_rows": int((~mask).sum()),
        }

    @classmethod
    def _random_split(cls, x_all, y_all) -> dict:
        stratify = y_all if int(np.min(np.bincount(y_all))) >= 2 else None
        x_tr, x_va, y_tr, y_va = train_test_split(
            x_all, y_all, test_size=_HOLDOUT_RATIO, random_state=42, stratify=stratify
        )
        return {"x_tr": x_tr, "y_tr": y_tr, "x_va": x_va, "y_va": y_va, "train_rows": int(len(x_tr))}

    @classmethod
    def _score_booster(cls, booster, x_va, y_va, train_rows: int) -> dict:
        empty = {
            "val_auc": None, "val_accuracy": None, "val_pr_auc": None,
            "train_rows": int(train_rows), "val_rows": int(len(x_va)),
        }
        if len(x_va) == 0 or len(np.unique(y_va)) < 2:
            return empty
        probs = booster.predict(x_va)
        preds = (probs >= 0.5).astype(np.int32)
        return {
            "val_auc": round(float(roc_auc_score(y_va, probs)), 4),
            "val_accuracy": round(float(accuracy_score(y_va, preds)), 4),
            "val_pr_auc": round(float(average_precision_score(y_va, probs)), 4),
            "train_rows": int(train_rows),
            "val_rows": int(len(x_va)),
        }

    @staticmethod
    def _pos_weight(y_train: np.ndarray) -> float:
        pos = int(np.sum(y_train == 1))
        neg = int(np.sum(y_train == 0))
        return float(neg / pos) if pos else 1.0

    @classmethod
    def _fit_lgbm(
        cls,
        x_train: np.ndarray,
        y_train: np.ndarray,
        *,
        x_va: np.ndarray | None = None,
        y_va: np.ndarray | None = None,
        num_boost_round: int | None = None,
    ):
        import lightgbm as lgb

        train_set = lgb.Dataset(x_train, label=y_train)
        params = {
            "objective": "binary",
            "metric": "auc",
            "learning_rate": 0.05,
            "num_leaves": 23,
            "min_data_in_leaf": 25,
            "feature_fraction": 0.85,
            "bagging_fraction": 0.8,
            "bagging_freq": 1,
            "scale_pos_weight": cls._pos_weight(y_train),
            "verbose": -1,
            "seed": 42,
        }
        if x_va is not None and y_va is not None and len(x_va) > 0:
            valid = lgb.Dataset(x_va, label=y_va, reference=train_set)
            return lgb.train(
                params,
                train_set,
                num_boost_round=_MAX_ROUNDS,
                valid_sets=[valid],
                valid_names=["val"],
                callbacks=[lgb.early_stopping(_EARLY_STOP, verbose=False), lgb.log_evaluation(0)],
            )
        return lgb.train(params, train_set, num_boost_round=num_boost_round or 120)

    def _fit_clusters(self, train_rows: list[LabeledTrainRow], names, scaler, booster):
        x = np.array([row.values for row in train_rows], dtype=np.float32)
        x_scaled = scaler.transform(x)
        cluster_count = max(3, min(12, len(train_rows) // 40))
        kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
        labels = kmeans.fit_predict(x_scaled)
        return kmeans, self._mean_shap_by_cluster(booster, x_scaled, labels, names)

    @staticmethod
    def _mean_shap_by_cluster(booster, x_scaled, labels, names: list[str]) -> dict[int, dict[str, float]]:
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
            coef = _sim_coef(name)
            self.db.add(
                CfgSimulationWeight(
                    feature_name=name,
                    base_importance=round(float(gain) / max_gain * 1000, 4),
                    impact_coefficient=coef,
                )
            )
        self.db.flush()


def _sim_coef(name: str) -> float:
    if name.startswith("survey_") or name.startswith("satisfaction"):
        return -0.25
    if "complaint" in name or name.startswith("ctype_") or name.startswith("ix_"):
        return 0.35
    if name in ("sat_gap", "ix_complaint_sat_gap", "ix_fee_loyalty_gap"):
        return 0.3
    return 0.2
