from fastapi import APIRouter, Depends, Query

from app import schemas
from app.core.deps import get_complaint_service
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("/init-categories", response_model=list[schemas.ComplaintCategoryRead])
def init_categories(
    service: ComplaintService = Depends(get_complaint_service),
) -> list[schemas.ComplaintCategoryRead]:
    return service.init_categories()


@router.post("/seed", response_model=schemas.ComplaintSeedResult)
def seed_complaints(
    count: int = Query(default=500, ge=1, le=2000),
    service: ComplaintService = Depends(get_complaint_service),
) -> schemas.ComplaintSeedResult:
    return service.seed_complaints(count=count)


@router.post("/classify", response_model=schemas.ComplaintClassifyResult)
def classify_complaints(
    service: ComplaintService = Depends(get_complaint_service),
) -> schemas.ComplaintClassifyResult:
    return service.classify_all()


@router.get("/stats", response_model=schemas.ComplaintStatsReport)
def complaint_stats(
    service: ComplaintService = Depends(get_complaint_service),
) -> schemas.ComplaintStatsReport:
    return service.get_stats()


@router.get("/samples", response_model=list[schemas.ComplaintRead])
def complaint_samples(
    category_name: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    service: ComplaintService = Depends(get_complaint_service),
) -> list[schemas.ComplaintRead]:
    return service.get_samples(category_name=category_name, limit=limit)
