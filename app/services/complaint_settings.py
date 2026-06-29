from app.core.config import settings

_classify_threshold: float | None = None


def get_classify_threshold() -> float:
    global _classify_threshold
    if _classify_threshold is None:
        _classify_threshold = settings.complaint_classify_threshold
    return _classify_threshold


def set_classify_threshold(value: float) -> float:
    if value < 0.0 or value > 1.0:
        raise ValueError("classify_threshold must be between 0 and 1")
    global _classify_threshold
    _classify_threshold = round(value, 4)
    return _classify_threshold
