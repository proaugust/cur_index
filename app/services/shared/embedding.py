from functools import lru_cache
import logging
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

EMBEDDING_DIM = settings.embedding_dim


def resolve_embedding_device() -> str:
    raw = (settings.embedding_device or "auto").strip().lower()
    if raw == "cpu":
        return "cpu"
    if raw == "cuda":
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def resolve_embedding_batch_size(device: str | None = None) -> int:
    if settings.embedding_batch_size and settings.embedding_batch_size > 0:
        return int(settings.embedding_batch_size)
    dev = device or resolve_embedding_device()
    return 64 if str(dev).startswith("cuda") else 32


@lru_cache(maxsize=1)
def _get_model() -> "SentenceTransformer":
    from sentence_transformers import SentenceTransformer

    device = resolve_embedding_device()
    logger.info("加载 embedding 模型 device=%s batch_size=%s", device, resolve_embedding_batch_size(device))
    return SentenceTransformer(settings.embedding_model_name, device=device)


def warmup() -> None:
    """启动时预加载模型并走真实 query 路径，避免首次检索请求卡顿。"""
    embed_query("warmup")


def _encode(texts: list[str], *, show_progress: bool = False) -> list[list[float]]:
    if not texts:
        return []
    batch_size = resolve_embedding_batch_size()
    vectors = _get_model().encode(
        texts,
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=show_progress and len(texts) > 1,
    )
    return [vector.tolist() for vector in vectors]


def embed_text(text: str) -> list[float]:
    """文档/对称相似度场景（入库切块、投诉归类等）。"""
    return _encode([text])[0]


def embed_query(text: str) -> list[float]:
    """检索查询；BGE 等模型需在 query 前加 instruction。"""
    instruction = settings.embedding_query_instruction
    payload = f"{instruction}{text}" if instruction else text
    return _encode([payload])[0]


def embed_texts(texts: list[str], *, show_progress: bool = False) -> list[list[float]]:
    return _encode(texts, show_progress=show_progress)


def mean_vector(vectors: list[list[float]]) -> list[float]:
    if not vectors:
        return []
    dim = len(vectors[0])
    summed = [0.0] * dim
    for vector in vectors:
        for index, value in enumerate(vector):
            summed[index] += value
    count = float(len(vectors))
    averaged = [value / count for value in summed]
    norm = sum(value * value for value in averaged) ** 0.5
    if norm == 0:
        return averaged
    return [value / norm for value in averaged]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return float(sum(a * b for a, b in zip(left, right)))
