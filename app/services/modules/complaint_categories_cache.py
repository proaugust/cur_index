"""投诉分类列表 Redis / 内存缓存。"""

from __future__ import annotations

import hashlib
import logging

from app import schemas
from app.core.config import settings
from app.services.shared.memory_cache import memory_delete_by_prefix, memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_delete_by_prefix, cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_KEY_PREFIX = "complaints:categories:"


def categories_cache_key(*, name: str | None) -> str:
    token = (name or "").strip()
    if not token:
        return f"{_KEY_PREFIX}all"
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
    return f"{_KEY_PREFIX}n:{digest}"


def get_cached_categories(*, name: str | None) -> list[schemas.ComplaintCategoryDetail] | None:
    key = categories_cache_key(name=name)
    memory_payload = memory_get_json(key)
    if memory_payload is not None:
        try:
            return [schemas.ComplaintCategoryDetail.model_validate(item) for item in memory_payload]
        except Exception:
            logger.warning("投诉分类缓存反序列化失败 source=memory key=%s", key, exc_info=True)

    if not settings.redis_enabled:
        return None

    redis_payload = cache_get_json(key)
    if redis_payload is None:
        return None
    try:
        items = [schemas.ComplaintCategoryDetail.model_validate(item) for item in redis_payload]
    except Exception:
        logger.warning("投诉分类缓存反序列化失败 source=redis key=%s", key, exc_info=True)
        return None
    memory_set_json(key, redis_payload, ttl=settings.complaint_samples_cache_ttl)
    logger.info("投诉分类缓存命中 source=redis key=%s", key)
    return items


def set_cached_categories(*, name: str | None, items: list[schemas.ComplaintCategoryDetail]) -> None:
    key = categories_cache_key(name=name)
    payload = [item.model_dump(mode="json") for item in items]
    ttl = settings.complaint_samples_cache_ttl
    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)
    logger.info("投诉分类已写入缓存 key=%s ttl=%ss count=%s", key, ttl, len(items))


def invalidate_complaint_categories_cache() -> int:
    memory_deleted = memory_delete_by_prefix(_KEY_PREFIX)
    redis_deleted = cache_delete_by_prefix(_KEY_PREFIX) if settings.redis_enabled else 0
    total = memory_deleted + redis_deleted
    if total:
        logger.info("已清除投诉分类缓存 memory=%s redis=%s", memory_deleted, redis_deleted)
    return total
