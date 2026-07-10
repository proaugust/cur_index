from datetime import date

from fastapi import APIRouter, Depends, Query

from app import schemas
from app.core.config import settings
from app.core.deps import get_complaint_service
from app.core.permissions import require_permission
from app.core.rate_limit import rate_limit
from app.models import User
from app.services.modules.complaint_service import ComplaintService

router = APIRouter(prefix="/complaints", tags=["complaints"])


@router.post("", response_model=schemas.ComplaintCreateResult)
def create_complaint(
    payload: schemas.ComplaintCreate,
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.create", name="新增投诉")),
) -> schemas.ComplaintCreateResult:
    return service.create_complaint(payload)


@router.post("/init-categories", response_model=list[schemas.ComplaintCategoryRead])
def init_categories(
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.init-categories", name="初始化分类")),
) -> list[schemas.ComplaintCategoryRead]:
    return service.init_categories()


@router.post("/seed", response_model=schemas.ComplaintSeedResult)
def seed_complaints(
    count: int = Query(default=500, ge=1, le=2000),
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.seed", name="造数")),
) -> schemas.ComplaintSeedResult:
    return service.seed_complaints(count=count)


@router.post("/embed", response_model=schemas.ComplaintEmbedResult)
def embed_complaints(
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.embed", name="向量化")),
) -> schemas.ComplaintEmbedResult:
    return service.embed_complaints()


@router.post("/classify", response_model=schemas.ComplaintClassifyResult)
def classify_complaints(
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.classify", name="执行归类")),
) -> schemas.ComplaintClassifyResult:
    return service.classify_all()


@router.get("/settings", response_model=schemas.ComplaintSettings)
def get_complaint_settings(
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.settings", name="归类设置")),
) -> schemas.ComplaintSettings:
    return service.get_settings()


@router.put("/settings", response_model=schemas.ComplaintSettings)
def update_complaint_settings(
    payload: schemas.ComplaintSettingsUpdate,
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.settings", name="归类设置")),
) -> schemas.ComplaintSettings:
    return service.update_settings(payload)


@router.get("/categories", response_model=list[schemas.ComplaintCategoryDetail])
def list_complaint_categories(
    name: str | None = Query(default=None, description="分类名称模糊搜索"),
    service: ComplaintService = Depends(get_complaint_service),
    _: User = Depends(require_permission("81.categories", name="分类列表")),
) -> list[schemas.ComplaintCategoryDetail]:
    return service.list_categories(name=name)


@router.get("/stats", response_model=schemas.ComplaintStatsReport)
def complaint_stats(
    q: str | None = Query(default=None, description="自然语言聚合查询，由 LLM 解析后统计"),
    refresh: bool = Query(default=False, description="跳过缓存重新计算，结果写回缓存（24h 有效）"),
    service: ComplaintService = Depends(get_complaint_service),
    _rl: None = Depends(rate_limit("complaints:stats", limit=settings.rate_limit_complaints_stats)),
    _: User = Depends(require_permission("81.stats", name="多维统计")),
) -> schemas.ComplaintStatsReport:
    return service.get_stats(q=q, refresh=refresh)


@router.get("/samples", response_model=schemas.ComplaintSamplesPage)
def complaint_samples(
    address: str | None = Query(default=None, description="地区模糊搜索"),
    text: str | None = Query(default=None, description="投诉正文：有值时向量语义检索，否则不按正文过滤"),
    time_from: date | None = Query(default=None, description="投诉时间起（含当天）"),
    time_to: date | None = Query(default=None, description="投诉时间止（含当天）"),
    category_name: str | None = Query(default=None, description="投诉分类名称"),
    is_classified: bool | None = Query(default=None, description="是否已归类：true 已归类，false 未归类"),
    min_similarity: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="最低相似度：有正文时按查询↔投诉过滤；无正文时按归类分过滤",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: ComplaintService = Depends(get_complaint_service),
    _rl: None = Depends(rate_limit("complaints:samples", limit=settings.rate_limit_complaints_samples)),
    _: User = Depends(require_permission("81.samples", name="样本列表")),
) -> schemas.ComplaintSamplesPage:
    return service.search_samples(
        address=address,
        text=text,
        time_from=time_from,
        time_to=time_to,
        category_name=category_name,
        classified=is_classified,
        min_similarity=min_similarity,
        page=page,
        page_size=page_size,
    )
