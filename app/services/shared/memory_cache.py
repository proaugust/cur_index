import logging
import time
from collections import OrderedDict
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class TtlLruCache:
    def __init__(self, maxsize: int) -> None:
        self._maxsize = max(1, maxsize)
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if time.monotonic() > expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any, *, ttl: int) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + max(1, ttl), value)
            self._data.move_to_end(key)
            while len(self._data) > self._maxsize:
                self._data.popitem(last=False)

    def delete_by_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [key for key in self._data if key.startswith(prefix)]
            for key in keys:
                del self._data[key]
            return len(keys)


_cache: TtlLruCache | None = None


def get_memory_cache() -> TtlLruCache | None:
    from app.core.config import settings

    if not settings.complaint_stats_memory_cache_enabled:
        return None
    global _cache
    if _cache is None:
        _cache = TtlLruCache(settings.complaint_stats_memory_cache_maxsize)
    return _cache


def memory_get_json(key: str) -> Any | None:
    cache = get_memory_cache()
    if cache is None:
        return None
    return cache.get(key)


def memory_set_json(key: str, value: Any, *, ttl: int) -> None:
    cache = get_memory_cache()
    if cache is None:
        return
    cache.set(key, value, ttl=ttl)


def memory_delete_by_prefix(prefix: str) -> int:
    cache = get_memory_cache()
    if cache is None:
        return 0
    return cache.delete_by_prefix(prefix)
