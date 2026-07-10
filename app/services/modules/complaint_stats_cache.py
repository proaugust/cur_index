import hashlib
import logging

from app import schemas
from app.core.config import settings
from app.services.shared.memory_cache import memory_delete_by_prefix, memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_delete_by_prefix, cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_KEY_PREFIX = "complaints:stats:"


def _normalize_query(q: str) -> str:
    return " ".join(q.strip().split())


def stats_cache_key(q: str | None) -> str:
    if not q or not q.strip():
        return f"{_KEY_PREFIX}default"
    digest = hashlib.sha256(_normalize_query(q).encode("utf-8")).hexdigest()[:16]
    return f"{_KEY_PREFIX}q:{digest}"


def _cache_ttl(q: str | None) -> int:
    if q and q.strip():
        return settings.complaint_stats_nl_cache_ttl
    return settings.complaint_stats_cache_ttl


def _parse_stats_payload(key: str, payload: object, *, source: str) -> schemas.ComplaintStatsReport | None:
    try:
        report = schemas.ComplaintStatsReport.model_validate(payload)
    except Exception:
        logger.warning("投诉统计缓存反序列化失败 source=%s key=%s", source, key, exc_info=True)
        return None
    logger.info("投诉统计缓存命中 source=%s key=%s", source, key)
    return report


def get_cached_stats(q: str | None) -> schemas.ComplaintStatsReport | None:
    key = stats_cache_key(q)

    memory_payload = memory_get_json(key)
    if memory_payload is not None:
        report = _parse_stats_payload(key, memory_payload, source="memory")
        if report is not None:
            return report

    if not settings.redis_enabled:
        return None

    redis_payload = cache_get_json(key)
    if redis_payload is None:
        return None

    report = _parse_stats_payload(key, redis_payload, source="redis")
    if report is not None:
        memory_set_json(key, redis_payload, ttl=_cache_ttl(q))
    return report


def set_cached_stats(q: str | None, report: schemas.ComplaintStatsReport) -> None:
    key = stats_cache_key(q)
    payload = report.model_dump(mode="json")
    ttl = _cache_ttl(q)

    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)

    backends = ["memory"]
    if settings.redis_enabled:
        backends.append("redis")
    logger.info("投诉统计已写入缓存 backends=%s key=%s ttl=%ss", "+".join(backends), key, ttl)


def invalidate_complaint_stats_cache() -> int:
    memory_deleted = memory_delete_by_prefix(_KEY_PREFIX)
    redis_deleted = cache_delete_by_prefix(_KEY_PREFIX) if settings.redis_enabled else 0
    total = memory_deleted + redis_deleted
    if total:
        logger.info("已清除投诉统计缓存 memory=%s redis=%s", memory_deleted, redis_deleted)
    return total
