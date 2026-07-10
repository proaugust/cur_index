"""模型文件加载、版本与 fallback。"""

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class InsightModelArtifacts:
    version: str
    feature_names: list[str]
    scaler: object
    kmeans: object | None
    cluster_shap: dict[int, dict[str, float]]


class InsightModelRegistry:
    def __init__(self) -> None:
        self.model_dir = settings.insight_model_dir
        self.model_path = self.model_dir / "lgbm-risk.txt"
        self.artifacts_path = self.model_dir / "artifacts.pkl"

    def has_model(self) -> bool:
        return self.model_path.is_file() and self.artifacts_path.is_file()

    def load_booster(self):
        import lightgbm as lgb

        return lgb.Booster(model_file=str(self.model_path))

    def load_artifacts(self) -> InsightModelArtifacts:
        with self.artifacts_path.open("rb") as handle:
            payload = pickle.load(handle)
        return InsightModelArtifacts(**payload)

    def save(self, booster, artifacts: InsightModelArtifacts) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        booster.save_model(str(self.model_path))
        with self.artifacts_path.open("wb") as handle:
            pickle.dump(artifacts.__dict__, handle)
        logger.info("Insight 模型已保存 version=%s path=%s", artifacts.version, self.model_dir)

    def resolve_version(self) -> str:
        if not self.has_model():
            return "mock-v1.0"
        return self.load_artifacts().version
