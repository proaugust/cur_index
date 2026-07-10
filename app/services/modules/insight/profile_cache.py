"""Insight 单客画像 Redis / 内存缓存。"""

import logging

from app.core.config import settings
from app.schemas.insight import InsightUserProfileResponse
from app.services.shared.memory_cache import memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_KEY_PREFIX = "cache:customer:"


def customer_profile_cache_key(user_id: str) -> str:
    return f"{_KEY_PREFIX}{user_id}"


def get_cached_profile(user_id: str) -> InsightUserProfileResponse | None:
    key = customer_profile_cache_key(user_id)
    ttl = settings.insight_profile_cache_ttl

    memory_payload = memory_get_json(key)
    if memory_payload is not None:
        return _parse_payload(key, memory_payload, source="memory", ttl=ttl)

    if not settings.redis_enabled:
        return None

    redis_payload = cache_get_json(key)
    if redis_payload is None:
        return None

    profile = _parse_payload(key, redis_payload, source="redis", ttl=ttl)
    if profile is not None:
        memory_set_json(key, redis_payload, ttl=ttl)
    return profile


def set_cached_profile(user_id: str, profile: InsightUserProfileResponse) -> None:
    key = customer_profile_cache_key(user_id)
    payload = profile.model_dump(mode="json")
    ttl = settings.insight_profile_cache_ttl

    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)

    backends = ["memory"]
    if settings.redis_enabled:
        backends.append("redis")
    logger.info("Insight 热点画像已缓存 backends=%s key=%s ttl=%ss", "+".join(backends), key, ttl)


def clear_all_profile_cache() -> None:
    """快照重算后清空画像缓存，避免列表/详情仍读到旧的空风险分。"""
    from app.services.shared.memory_cache import memory_delete_by_prefix
    from app.services.shared.redis_client import cache_delete_by_prefix

    memory_n = memory_delete_by_prefix(_KEY_PREFIX)
    redis_n = cache_delete_by_prefix(_KEY_PREFIX) if settings.redis_enabled else 0
    logger.info("Insight 画像缓存已清空 memory=%s redis=%s", memory_n, redis_n)


def _parse_payload(key: str, payload: object, *, source: str, ttl: int) -> InsightUserProfileResponse | None:
    try:
        profile = InsightUserProfileResponse.model_validate(payload)
    except Exception:
        logger.warning("Insight 画像缓存反序列化失败 source=%s key=%s", source, key, exc_info=True)
        return None
    profile.cache.hit = True
    profile.cache.source = source
    profile.cache.ttl_seconds = ttl
    logger.info("Insight 画像缓存命中 source=%s key=%s", source, key)
    return profile
