from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings

EMBEDDING_DIM = settings.embedding_dim


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


def warmup() -> None:
    """启动时预加载模型并走真实 query 路径，避免首次检索请求卡顿。"""
    embed_query("warmup")


def _encode(texts: list[str], *, show_progress: bool = False) -> list[list[float]]:
    if not texts:
        return []
    vectors = _get_model().encode(
        texts,
        normalize_embeddings=True,
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
