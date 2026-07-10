"""Insight 投诉文本向量化。"""

from app.services.modules.insight.constants import COMPLAINT_VECTOR_DIM
from app.services.shared.embedding import embed_text, embed_texts


def _fit_vector_dim(vector: list[float]) -> list[float]:
    """将共享 embedding 输出规范为 Insight 投诉向量维度。"""
    if len(vector) == COMPLAINT_VECTOR_DIM:
        return vector
    if len(vector) > COMPLAINT_VECTOR_DIM:
        return vector[:COMPLAINT_VECTOR_DIM]
    return [*vector, *([0.0] * (COMPLAINT_VECTOR_DIM - len(vector)))]


def embed_complaint_text(text: str) -> list[float]:
    return _fit_vector_dim(embed_text(text))


def embed_complaint_texts(texts: list[str], *, show_progress: bool = False) -> list[list[float]]:
    return [_fit_vector_dim(vector) for vector in embed_texts(texts, show_progress=show_progress)]
