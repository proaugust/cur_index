import hashlib
import json
import logging
from datetime import date

from app import schemas
from app.core.config import settings
from app.services.shared.memory_cache import memory_delete_by_prefix, memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_delete_by_prefix, cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_KEY_PREFIX = "complaints:samples:"


def samples_cache_key(
    *,
    address: str | None,
    text: str | None,
    time_from: date | None,
    time_to: date | None,
    category_name: str | None,
    classified: bool | None,
    min_similarity: float | None,
    page: int,
    page_size: int,
) -> str:
    payload = {
        "address": (address or "").strip(),
        "text": (text or "").strip(),
        "time_from": time_from.isoformat() if time_from else "",
        "time_to": time_to.isoformat() if time_to else "",
        "category_name": (category_name or "").strip(),
        "classified": classified,
        "min_similarity": None if min_similarity is None else round(float(min_similarity), 4),
        "page": page,
        "page_size": page_size,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return f"{_KEY_PREFIX}{digest}"


def _cache_ttl() -> int:
    return settings.complaint_samples_cache_ttl


def _parse_samples_payload(key: str, payload: object, *, source: str) -> schemas.ComplaintSamplesPage | None:
    try:
        page = schemas.ComplaintSamplesPage.model_validate(payload)
    except Exception:
        logger.warning("投诉样本缓存反序列化失败 source=%s key=%s", source, key, exc_info=True)
        return None
    logger.info("投诉样本缓存命中 source=%s key=%s", source, key)
    return page


def get_cached_samples(
    *,
    address: str | None,
    text: str | None,
    time_from: date | None,
    time_to: date | None,
    category_name: str | None,
    classified: bool | None,
    min_similarity: float | None,
    page: int,
    page_size: int,
) -> schemas.ComplaintSamplesPage | None:
    key = samples_cache_key(
        address=address,
        text=text,
        time_from=time_from,
        time_to=time_to,
        category_name=category_name,
        classified=classified,
        min_similarity=min_similarity,
        page=page,
        page_size=page_size,
    )

    memory_payload = memory_get_json(key)
    if memory_payload is not None:
        report = _parse_samples_payload(key, memory_payload, source="memory")
        if report is not None:
            return report

    if not settings.redis_enabled:
        return None

    redis_payload = cache_get_json(key)
    if redis_payload is None:
        return None

    report = _parse_samples_payload(key, redis_payload, source="redis")
    if report is not None:
        memory_set_json(key, redis_payload, ttl=_cache_ttl())
    return report


def set_cached_samples(
    *,
    address: str | None,
    text: str | None,
    time_from: date | None,
    time_to: date | None,
    category_name: str | None,
    classified: bool | None,
    min_similarity: float | None,
    page: int,
    page_size: int,
    result: schemas.ComplaintSamplesPage,
) -> None:
    key = samples_cache_key(
        address=address,
        text=text,
        time_from=time_from,
        time_to=time_to,
        category_name=category_name,
        classified=classified,
        min_similarity=min_similarity,
        page=page,
        page_size=page_size,
    )
    payload = result.model_dump(mode="json")
    ttl = _cache_ttl()

    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)

    backends = ["memory"]
    if settings.redis_enabled:
        backends.append("redis")
    logger.info("投诉样本已写入缓存 backends=%s key=%s ttl=%ss", "+".join(backends), key, ttl)


def invalidate_complaint_samples_cache() -> int:
    memory_deleted = memory_delete_by_prefix(_KEY_PREFIX)
    redis_deleted = cache_delete_by_prefix(_KEY_PREFIX) if settings.redis_enabled else 0
    total = memory_deleted + redis_deleted
    if total:
        logger.info("已清除投诉样本缓存 memory=%s redis=%s", memory_deleted, redis_deleted)
    return total
