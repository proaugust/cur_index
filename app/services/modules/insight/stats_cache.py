"""Insight 统计类接口 Redis / 内存缓存。"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import date
from typing import TypeVar

from pydantic import BaseModel

from app.core.config import settings
from app.schemas.insight import (
    InsightDecisionDashboard,
    InsightRegionRiskMetricsListResponse,
    InsightSeedStatus,
)
from app.services.shared.memory_cache import memory_delete_by_prefix, memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_delete_by_prefix, cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_SEED_KEY = "insight:stats:seed-status"
_DASHBOARD_KEY = "insight:stats:decision-dashboard"
_REGION_PREFIX = "insight:stats:region-metrics:"
_ALL_PREFIX = "insight:stats:"

T = TypeVar("T", bound=BaseModel)


def _ttl() -> int:
    return settings.insight_stats_cache_ttl


def _get(key: str, model: type[T]) -> T | None:
    memory_payload = memory_get_json(key)
    if memory_payload is not None:
        try:
            return model.model_validate(memory_payload)
        except Exception:
            logger.warning("Insight 统计缓存反序列化失败 source=memory key=%s", key, exc_info=True)

    if not settings.redis_enabled:
        return None

    redis_payload = cache_get_json(key)
    if redis_payload is None:
        return None
    try:
        parsed = model.model_validate(redis_payload)
    except Exception:
        logger.warning("Insight 统计缓存反序列化失败 source=redis key=%s", key, exc_info=True)
        return None
    memory_set_json(key, redis_payload, ttl=_ttl())
    logger.info("Insight 统计缓存命中 source=redis key=%s", key)
    return parsed


def _set(key: str, value: BaseModel) -> None:
    payload = value.model_dump(mode="json")
    ttl = _ttl()
    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)
    logger.info("Insight 统计已写入缓存 key=%s ttl=%ss", key, ttl)


def get_cached_seed_status() -> InsightSeedStatus | None:
    return _get(_SEED_KEY, InsightSeedStatus)


def set_cached_seed_status(status: InsightSeedStatus) -> None:
    _set(_SEED_KEY, status)


def get_cached_decision_dashboard() -> InsightDecisionDashboard | None:
    return _get(_DASHBOARD_KEY, InsightDecisionDashboard)


def set_cached_decision_dashboard(dashboard: InsightDecisionDashboard) -> None:
    _set(_DASHBOARD_KEY, dashboard)


def region_metrics_cache_key(
    *,
    snapshot_date: date | None,
    region_l1: str | None,
    region_l2: str | None,
    page: int,
    page_size: int,
) -> str:
    payload = {
        "snapshot_date": snapshot_date.isoformat() if snapshot_date else "",
        "region_l1": (region_l1 or "").strip(),
        "region_l2": (region_l2 or "").strip(),
        "page": page,
        "page_size": page_size,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return f"{_REGION_PREFIX}{digest}"


def get_cached_region_metrics(
    *,
    snapshot_date: date | None,
    region_l1: str | None,
    region_l2: str | None,
    page: int,
    page_size: int,
) -> InsightRegionRiskMetricsListResponse | None:
    key = region_metrics_cache_key(
        snapshot_date=snapshot_date,
        region_l1=region_l1,
        region_l2=region_l2,
        page=page,
        page_size=page_size,
    )
    return _get(key, InsightRegionRiskMetricsListResponse)


def set_cached_region_metrics(
    *,
    snapshot_date: date | None,
    region_l1: str | None,
    region_l2: str | None,
    page: int,
    page_size: int,
    result: InsightRegionRiskMetricsListResponse,
) -> None:
    key = region_metrics_cache_key(
        snapshot_date=snapshot_date,
        region_l1=region_l1,
        region_l2=region_l2,
        page=page,
        page_size=page_size,
    )
    _set(key, result)


def invalidate_insight_stats_cache() -> int:
    memory_deleted = memory_delete_by_prefix(_ALL_PREFIX)
    redis_deleted = cache_delete_by_prefix(_ALL_PREFIX) if settings.redis_enabled else 0
    total = memory_deleted + redis_deleted
    if total:
        logger.info("已清除 Insight 统计缓存 memory=%s redis=%s", memory_deleted, redis_deleted)
    return total
