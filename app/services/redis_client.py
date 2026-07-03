import json
import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)
_redis_ok: bool | None = None


@lru_cache(maxsize=1)
def _redis_client():
    import redis

    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        protocol=2,
        socket_connect_timeout=settings.redis_socket_timeout,
        socket_timeout=settings.redis_socket_timeout,
    )


def _redis_enabled() -> bool:
    global _redis_ok
    if not settings.redis_enabled:
        return False
    if _redis_ok is False:
        return False
    if _redis_ok is True:
        return True
    try:
        _redis_ok = bool(_redis_client().ping())
        if not _redis_ok:
            logger.warning("Redis PING 未返回 PONG")
    except Exception:
        _redis_ok = False
        logger.warning("Redis 不可用，跳过缓存", exc_info=True)
    return _redis_ok


def _mark_redis_unavailable() -> None:
    global _redis_ok
    _redis_ok = False


def cache_get_json(key: str) -> Any | None:
    if not _redis_enabled():
        return None
    try:
        raw = _redis_client().get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        _mark_redis_unavailable()
        logger.warning("Redis 读取失败 key=%s", key, exc_info=True)
        return None


def cache_set_json(key: str, value: Any, *, ttl: int) -> None:
    if not _redis_enabled():
        return
    try:
        _redis_client().setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
    except Exception:
        _mark_redis_unavailable()
        logger.warning("Redis 写入失败 key=%s", key, exc_info=True)


def cache_delete_by_prefix(prefix: str) -> int:
    if not _redis_enabled():
        return 0
    deleted = 0
    try:
        client = _redis_client()
        for key in client.scan_iter(match=f"{prefix}*"):
            deleted += int(client.delete(key) or 0)
    except Exception:
        _mark_redis_unavailable()
        logger.warning("Redis 批量删除失败 prefix=%s", prefix, exc_info=True)
    return deleted
