from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.system.login_log_service import query_login_logs

router = APIRouter(prefix="/login-logs", tags=["login-logs"])


@router.get("", response_model=schemas.LoginLogListResponse)
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
    return schemas.LoginLogListResponse(
        items=[schemas.LoginLogItem.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )
