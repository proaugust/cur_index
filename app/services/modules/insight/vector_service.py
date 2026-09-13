"""Insight 投诉文本向量化。"""

from __future__ import annotations

import logging
import math
import random

from app.services.modules.insight.constants import COMPLAINT_VECTOR_DIM
from app.services.modules.insight.seed.complaint_templates import (
    TemplateEmbedKey,
    list_canonical_template_texts,
)
from app.services.shared.embedding import embed_text, embed_texts

logger = logging.getLogger(__name__)

_seed_template_vectors: dict[TemplateEmbedKey, list[float]] | None = None
_NOISE_RANDOM = random.Random(20260310)


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


def _with_micro_noise(vector: list[float], *, scale: float = 0.01) -> list[float]:
    """同模板复用时加微噪声并重归一化，避免完全相同向量。"""
    noisy = [v + scale * (_NOISE_RANDOM.random() * 2.0 - 1.0) for v in vector]
    norm = math.sqrt(sum(x * x for x in noisy)) or 1.0
    return [x / norm for x in noisy]


def get_seed_template_vectors(*, show_progress: bool = True) -> dict[TemplateEmbedKey, list[float]]:
    """按模板预嵌入（真 BGE）；进程内缓存，造数千条样本只 encode 一次模板集。"""
    global _seed_template_vectors
    if _seed_template_vectors is not None:
        return _seed_template_vectors
    specs = list_canonical_template_texts()
    texts = [text for _, text in specs]
    logger.info("Insight 种子模板预嵌入 count=%s", len(texts))
    vectors = embed_complaint_texts(texts, show_progress=show_progress)
    _seed_template_vectors = {key: vector for (key, _), vector in zip(specs, vectors)}
    return _seed_template_vectors


def vector_for_seed_template(key: TemplateEmbedKey, cache: dict[TemplateEmbedKey, list[float]]) -> list[float]:
    base = cache.get(key)
    if base is None:
        # 兜底：同分类任意模板 / 默认键
        for (ctype, stype, _), vec in cache.items():
            if ctype == key[0] and stype == key[1]:
                base = vec
                break
        if base is None:
            base = cache.get(("其它", "其他问题", -1)) or next(iter(cache.values()))
    return _with_micro_noise(base)
