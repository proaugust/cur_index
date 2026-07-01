from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.llm_usage_service import get_recent_logs, get_usage_stats

router = APIRouter(prefix="/llm-usage", tags=["llm-usage"])


@router.get("/stats", response_model=schemas.LlmUsageStatsResponse)
def read_usage_stats(
    days: int = Query(7, ge=1, le=90),
    exclude_warmup: bool = Query(True),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("90.stats")),
) -> schemas.LlmUsageStatsResponse:
    return schemas.LlmUsageStatsResponse(**get_usage_stats(db, days=days, exclude_warmup=exclude_warmup))


@router.get("/recent", response_model=schemas.LlmUsageRecentResponse)
def read_recent_usage(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("90.recent")),
) -> schemas.LlmUsageRecentResponse:
    rows = get_recent_logs(db, limit=limit)
    return schemas.LlmUsageRecentResponse(items=[schemas.LlmUsageLogItem(**row) for row in rows])
