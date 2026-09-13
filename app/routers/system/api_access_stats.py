from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.core.config import settings
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.shared.memory_cache import memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_get_json, cache_set_json
from app.services.system.api_access_stat_service import query_api_access_stats

router = APIRouter(prefix="/api-access-stats", tags=["api-access-stats"])


def _api_access_cache_key(*, page: int, page_size: int, username: str | None, days: int | None) -> str:
    user_part = (username or "").strip()
    days_part = str(days) if days is not None else "all"
    return f"stats:api-access:p={page}:s={page_size}:u={user_part}:d={days_part}"


@router.get("", response_model=schemas.ApiAccessStatListResponse)
def list_api_access_stats(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    username: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    refresh: bool = Query(default=False, description="跳过缓存重新统计，结果写回 Redis"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("15.list", name="接口访问统计")),
) -> schemas.ApiAccessStatListResponse:
    key = _api_access_cache_key(page=page, page_size=page_size, username=username, days=days)
    ttl = settings.api_access_stats_cache_ttl
    if not refresh:
        payload = memory_get_json(key)
        if payload is None and settings.redis_enabled:
            payload = cache_get_json(key)
            if payload is not None:
                memory_set_json(key, payload, ttl=ttl)
        if payload is not None:
            try:
                return schemas.ApiAccessStatListResponse.model_validate(payload)
            except Exception:
                pass

    rows, total = query_api_access_stats(
        db,
        page=page,
        page_size=page_size,
        username=username,
        days=days,
    )
    items = [
        schemas.ApiAccessStatItem(
            id=stat.id,
            user_id=stat.user_id,
            username=uname,
            method=stat.method,
            path=stat.path,
            hit_count=stat.hit_count,
            last_status=stat.last_status,
            last_at=stat.last_at,
        )
        for stat, uname in rows
    ]
    result = schemas.ApiAccessStatListResponse(items=items, total=total, page=page, page_size=page_size)
    payload = result.model_dump(mode="json")
    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)
    return result
