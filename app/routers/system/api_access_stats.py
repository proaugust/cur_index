from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
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


def _parse_dt(value: str | None) -> datetime | None:
    if value is None or not value.strip():
        return None
    raw = value.strip().replace("T", " ")[:19]
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="时间格式应为 YYYY-MM-DD HH:mm:ss") from exc


def _api_access_cache_key(**parts: object) -> str:
    raw = "|".join(f"{key}={'' if value is None else value}" for key, value in sorted(parts.items()))
    return f"stats:api-access:{raw}"


@router.get("/list", response_model=schemas.ApiAccessStatListResponse)
def list_api_access_stats(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    username: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    start: str | None = Query(None),
    end: str | None = Query(None),
    page_name: str | None = Query(None),
    path: str | None = Query(None),
    method: str | None = Query(None),
    hit_count: int | None = Query(None, ge=0),
    status_code: int | None = Query(None, ge=100, le=599),
    refresh: bool = Query(default=False, description="跳过缓存重新统计，结果写回 Redis"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("15.list", name="接口访问统计")),
) -> schemas.ApiAccessStatListResponse:
    start_at = _parse_dt(start)
    end_at = _parse_dt(end)
    key = _api_access_cache_key(
        page=page,
        page_size=page_size,
        username=(username or "").strip(),
        days=days,
        start=start_at.isoformat(sep=" ") if start_at else "",
        end=end_at.isoformat(sep=" ") if end_at else "",
        page_name=(page_name or "").strip(),
        path=(path or "").strip(),
        method=(method or "").strip().upper(),
        hit_count=hit_count,
        status_code=status_code,
    )
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
        start=start_at,
        end=end_at,
        page_name=page_name,
        path=path,
        method=method,
        hit_count=hit_count,
        status_code=status_code,
    )
    items = [schemas.ApiAccessStatItem(**row) for row in rows]
    result = schemas.ApiAccessStatListResponse(items=items, total=total, page=page, page_size=page_size)
    payload = result.model_dump(mode="json")
    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)
    return result
