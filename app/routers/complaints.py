from datetime import date

from fastapi import APIRouter, Depends, Query

from app import schemas
from app.core.deps import get_complaint_service
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("/init-categories", response_model=list[schemas.ComplaintCategoryRead])
def init_categories(service: ComplaintService = Depends(get_complaint_service)) -> list[schemas.ComplaintCategoryRead]:
    return service.init_categories()


@router.post("/seed", response_model=schemas.ComplaintSeedResult)
def seed_complaints(
    count: int = Query(default=500, ge=1, le=2000), service: ComplaintService = Depends(get_complaint_service)
) -> schemas.ComplaintSeedResult:
    return service.seed_complaints(count=count)


@router.post("/embed", response_model=schemas.ComplaintEmbedResult)
def embed_complaints(service: ComplaintService = Depends(get_complaint_service)) -> schemas.ComplaintEmbedResult:
    return service.embed_complaints()


@router.post("/classify", response_model=schemas.ComplaintClassifyResult)
def classify_complaints(service: ComplaintService = Depends(get_complaint_service)) -> schemas.ComplaintClassifyResult:
    return service.classify_all()


@router.get("/stats", response_model=schemas.ComplaintStatsReport)
def complaint_stats(service: ComplaintService = Depends(get_complaint_service)) -> schemas.ComplaintStatsReport:
    return service.get_stats()


@router.get("/samples", response_model=schemas.ComplaintSamplesPage)
def complaint_samples(
    address: str | None = Query(default=None, description="地区模糊搜索"),
    text: str | None = Query(default=None, description="投诉正文模糊搜索"),
    time_from: date | None = Query(default=None, description="投诉时间起（含当天）"),
    time_to: date | None = Query(default=None, description="投诉时间止（含当天）"),
    category_name: str | None = Query(default=None, description="投诉分类名称"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: ComplaintService = Depends(get_complaint_service),
) -> schemas.ComplaintSamplesPage:
    return service.search_samples(
        address=address,
        text=text,
        time_from=time_from,
        time_to=time_to,
        category_name=category_name,
        page=page,
        page_size=page_size,
    )
