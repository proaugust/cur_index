from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.ops.error_log_service import query_error_logs, update_error_status

router = APIRouter(prefix="/error-logs", tags=["error-logs"])


@router.get("", response_model=schemas.AppErrorLogListResponse)
def list_error_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    source: str | None = Query(None),
    level: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    error_type: str | None = Query(None),
    request_id: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("92.list", name="错误日志列表")),
) -> schemas.AppErrorLogListResponse:
    rows, total = query_error_logs(
        db,
        page=page,
        page_size=page_size,
        source=source,
        level=level,
        status=status_filter,
        error_type=error_type,
        request_id=request_id,
        days=days,
    )
    return schemas.AppErrorLogListResponse(
        items=[schemas.AppErrorLogItem.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/{error_id}/status", response_model=schemas.AppErrorLogItem)
def patch_error_status(
    error_id: int,
    payload: schemas.AppErrorLogStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("92.resolve", name="错误日志状态")),
) -> schemas.AppErrorLogItem:
    row = update_error_status(db, error_id, payload.status)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="错误日志不存在")
    return schemas.AppErrorLogItem.model_validate(row)
