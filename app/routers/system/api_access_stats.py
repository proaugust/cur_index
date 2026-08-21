from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.system.api_access_stat_service import query_api_access_stats

router = APIRouter(prefix="/api-access-stats", tags=["api-access-stats"])


@router.get("", response_model=schemas.ApiAccessStatListResponse)
def list_api_access_stats(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    username: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("15.list", name="接口访问统计")),
) -> schemas.ApiAccessStatListResponse:
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
    return schemas.ApiAccessStatListResponse(items=items, total=total, page=page, page_size=page_size)
