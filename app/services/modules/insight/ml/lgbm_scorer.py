"""LightGBM 批量推理。"""

from decimal import Decimal

import numpy as np

from app.services.modules.insight.ml.model_registry import InsightModelRegistry
from app.services.modules.insight.ml.types import UserFeatureRow


class LgbmRiskScorer:
    def __init__(self, registry: InsightModelRegistry | None = None):
        self.registry = registry or InsightModelRegistry()
        self._booster = None
        self._artifacts = None

    def _ensure_loaded(self) -> None:
        if self._booster is None:
            self._booster = self.registry.load_booster()
            self._artifacts = self.registry.load_artifacts()

    @property
    def artifacts(self):
        self._ensure_loaded()
        return self._artifacts

    def predict_batch(self, features: dict[str, UserFeatureRow], *, dampen: float = 0.0) -> dict[str, Decimal]:
        self._ensure_loaded()
        assert self._artifacts is not None
        user_ids = list(features.keys())
        matrix = np.array([features[user_id].values for user_id in user_ids], dtype=np.float32)
        scaled = self._artifacts.scaler.transform(matrix)
        probs = self._booster.predict(scaled)
        if probs.ndim > 1:
            probs = probs[:, 1] if probs.shape[1] > 1 else probs[:, 0]
        scores: dict[str, Decimal] = {}
        for user_id, prob in zip(user_ids, probs.tolist()):
            value = max(0.05, float(prob) - dampen)
            scores[user_id] = Decimal(str(round(min(0.99, value), 4)))
        return scores
