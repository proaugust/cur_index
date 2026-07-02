from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.llm_usage_service import get_usage_stats, query_logs

router = APIRouter(prefix="/llm-usage", tags=["llm-usage"])


@router.get("/stats", response_model=schemas.LlmUsageStatsResponse)
def read_usage_stats(
    days: int | None = Query(default=None, ge=1, le=90),
    exclude_warmup: bool = Query(True),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("90.stats")),
) -> schemas.LlmUsageStatsResponse:
    return schemas.LlmUsageStatsResponse(**get_usage_stats(db, days=days, exclude_warmup=exclude_warmup))


@router.get("/recent", response_model=schemas.LlmUsageRecentResponse)
def read_recent_usage(
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=2000),
    caller: str | None = Query(None),
    username: str | None = Query(None),
    user_id: int | None = Query(None, ge=1),
    engine: str | None = Query(None),
    success: bool | None = Query(None),
    request_id: str | None = Query(None),
    days: int | None = Query(default=None, ge=1, le=90),
    exclude_warmup: bool = Query(True),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("90.recent")),
) -> schemas.LlmUsageRecentResponse:
    items, total = query_logs(
        db,
        page=page,
        page_size=page_size,
        caller=caller,
        username=username,
        user_id=user_id,
        engine=engine,
        success=success,
        request_id=request_id,
        days=days,
        exclude_warmup=exclude_warmup,
    )
    return schemas.LlmUsageRecentResponse(
        items=[schemas.LlmUsageLogItem(**row) for row in items],
        total=total,
        page=page,
        page_size=page_size,
    )
