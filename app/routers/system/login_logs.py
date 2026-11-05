from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.system.login_log_service import (
    query_activity,
    query_login_logs,
    query_page_views,
    record_page_view,
    summarize_user_agent,
)

router = APIRouter(prefix="/login-logs", tags=["login-logs"])


@router.get("/list", response_model=schemas.LoginLogListResponse)
def list_login_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    username: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("14.list", name="登录记录列表")),
) -> schemas.LoginLogListResponse:
    rows, total = query_login_logs(
        db,
        page=page,
        page_size=page_size,
        username=username,
        days=days,
    )
    items: list[schemas.LoginLogItem] = []
    for row in rows:
        browser, os_name = summarize_user_agent(row.user_agent)
        item = schemas.LoginLogItem.model_validate(row)
        item.browser = browser
        item.os = os_name
        items.append(item)
    return schemas.LoginLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/page-views")
def create_page_view(
    payload: schemas.PageViewCreate,
    current_user: User = Depends(get_current_user),
) -> dict[str, bool]:
    record_page_view(
        user_id=current_user.id,
        username=current_user.username,
        path=payload.path,
        title=payload.title,
    )
    return {"ok": True}


@router.get("/page-views", response_model=schemas.PageViewListResponse)
def list_page_views(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    username: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("14.list", name="登录记录列表")),
) -> schemas.PageViewListResponse:
    rows, total = query_page_views(
        db,
        page=page,
        page_size=page_size,
        username=username,
        days=days,
    )
    return schemas.PageViewListResponse(
        items=[schemas.PageViewItem.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/activity", response_model=schemas.ActivityListResponse)
def list_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    username: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("15.list", name="接口访问统计")),
) -> schemas.ActivityListResponse:
    rows, total = query_activity(
        db,
        page=page,
        page_size=page_size,
        username=username,
        days=days,
    )
    items = [
        schemas.ActivityItem(
            kind=row.kind,
            username=row.username or "",
            method=row.method or "",
            path=row.path or "",
            title=row.title,
            status_code=row.status_code,
            error=row.error,
            page=row.page,
            request_id=row.request_id,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return schemas.ActivityListResponse(items=items, total=total, page=page, page_size=page_size)
