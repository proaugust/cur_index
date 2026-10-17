"""hybrid_rerank 精排：BGE Cross-Encoder。加载失败时返回 None，调用方回退融合排序。"""

from __future__ import annotations

import logging
import math
from functools import lru_cache

from app.core.config import settings
from app.services.shared.embedding import resolve_embedding_device

logger = logging.getLogger(__name__)

_load_failed = False


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import CrossEncoder

    device = resolve_embedding_device()
    name = settings.reranker_model_name
    logger.info("加载 reranker 模型 %s device=%s", name, device)
    return CrossEncoder(name, device=device, max_length=512)


def _to_unit(values: list[float]) -> list[float]:
    if not values:
        return []
    if min(values) < 0 or max(values) > 1:
        values = [1.0 / (1.0 + math.exp(-max(min(v, 20.0), -20.0))) for v in values]
    return [round(v, 4) for v in values]


def score_passages(query: str, passages: list[str]) -> list[float] | None:
    """返回 0～1 相关分，与 passages 等长。模型不可用时返回 None。"""
    global _load_failed
    if _load_failed:
        return None
    if not query.strip() or not passages:
        return []
    try:
        raw = _get_model().predict(
            [(query, text) for text in passages],
            show_progress_bar=False,
            batch_size=16,
        )
        values = raw.tolist() if hasattr(raw, "tolist") else raw
        if isinstance(values, (float, int)):
            values = [values]
        scores = _to_unit([float(item) for item in values])
    except Exception:
        _load_failed = True
        logger.exception("reranker 不可用，hybrid_rerank 回退 C1 融合")
        return None
    if len(scores) != len(passages):
        logger.warning("reranker 分数条数不符 passages=%s scores=%s", len(passages), len(scores))
        return None
    return scores
