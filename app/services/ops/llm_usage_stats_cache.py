import logging

from app import schemas
from app.core.config import settings
from app.services.shared.memory_cache import memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_KEY_PREFIX = "llm:usage:stats:"


def stats_cache_key(*, days: int | None, exclude_warmup: bool) -> str:
    days_part = str(days) if days is not None else "all"
    warmup_part = "1" if exclude_warmup else "0"
    return f"{_KEY_PREFIX}days={days_part}:warmup={warmup_part}"


def get_cached_usage_stats(*, days: int | None, exclude_warmup: bool) -> schemas.LlmUsageStatsResponse | None:
    key = stats_cache_key(days=days, exclude_warmup=exclude_warmup)

    memory_payload = memory_get_json(key)
    if memory_payload is not None:
        report = _parse_payload(key, memory_payload, source="memory")
        if report is not None:
            return report

    if not settings.redis_enabled:
        return None

    redis_payload = cache_get_json(key)
    if redis_payload is None:
        return None

    report = _parse_payload(key, redis_payload, source="redis")
    if report is not None:
        memory_set_json(key, redis_payload, ttl=settings.llm_usage_stats_cache_ttl)
    return report


def set_cached_usage_stats(*, days: int | None, exclude_warmup: bool, report: schemas.LlmUsageStatsResponse) -> None:
    key = stats_cache_key(days=days, exclude_warmup=exclude_warmup)
    payload = report.model_dump(mode="json")
    ttl = settings.llm_usage_stats_cache_ttl

    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)

    backends = ["memory"]
    if settings.redis_enabled:
        backends.append("redis")
    logger.info("LLM 用量统计已写入缓存 backends=%s key=%s ttl=%ss", "+".join(backends), key, ttl)


def _parse_payload(key: str, payload: object, *, source: str) -> schemas.LlmUsageStatsResponse | None:
    try:
        report = schemas.LlmUsageStatsResponse.model_validate(payload)
    except Exception:
        logger.warning("LLM 用量统计缓存反序列化失败 source=%s key=%s", source, key, exc_info=True)
        return None
    logger.info("LLM 用量统计缓存命中 source=%s key=%s", source, key)
    return report
