"""API 限流：Redis 固定窗口计数，不可用时进程内兜底。"""

from __future__ import annotations

import logging
import time
from threading import Lock

from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.core.deps import get_current_user
from app.models import User
from app.services.redis_client import cache_incr

logger = logging.getLogger(__name__)

_MEMORY: dict[str, tuple[int, float]] = {}
_MEMORY_LOCK = Lock()


def _memory_incr(key: str, *, ttl: int) -> int:
    now = time.monotonic()
    with _MEMORY_LOCK:
        count, window_end = _MEMORY.get(key, (0, now + ttl))
        if now >= window_end:
            count, window_end = 0, now + ttl
        count += 1
        _MEMORY[key] = (count, window_end)
        return count


def _hit(key: str, *, limit: int, window_sec: int) -> tuple[bool, int]:
    count = cache_incr(key, ttl=window_sec)
    if count is None:
        count = _memory_incr(key, ttl=window_sec)
    allowed = count <= limit
    retry_after = max(1, window_sec // limit) if not allowed else 0
    return allowed, retry_after


def rate_limit(scope: str, *, limit: int, window_sec: int = 60):
    """按已登录用户限流，需与 require_permission 等鉴权依赖同路由使用。"""

    def checker(user: User = Depends(get_current_user)) -> None:
        if not settings.rate_limit_enabled:
            return
        key = f"rl:{scope}:u{user.id}"
        allowed, retry_after = _hit(key, limit=limit, window_sec=window_sec)
        if allowed:
            return
        logger.warning("限流触发 scope=%s user_id=%s limit=%s/%ss", scope, user.id, limit, window_sec)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(retry_after)},
        )

    return checker
