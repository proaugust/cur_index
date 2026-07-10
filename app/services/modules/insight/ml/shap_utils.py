"""将 SHAP 原始值规范到可读的 0~1 风险贡献尺度。"""

from app.services.modules.insight.ml.feature_labels import label_shap


def normalize_shap_dict(names: list[str], values: list[float], risk_score: float, *, limit: int = 8) -> dict[str, float]:
    pairs = sorted(zip(names, values), key=lambda item: abs(item[1]), reverse=True)[:limit]
    pairs = [(name, value) for name, value in pairs if abs(value) >= 1e-6]
    if not pairs:
        return {}
    total = sum(abs(value) for _, value in pairs) or 1.0
    scale = max(0.0, min(1.0, float(risk_score))) / total
    return {label_shap(name): round(float(value) * scale, 4) for name, value in pairs}
