from datetime import date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query

from sqlalchemy.orm import Session


from app.core.deps import get_db, get_insight_profile_service, get_insight_risk_snapshot_service, get_insight_seed_service

from app.core.permissions import require_permission

from app.crud import insight_data

from app.models import User

from app.schemas.insight import (
    InsightComplaintCategoryPair,
    InsightComplaintCreate,
    InsightComplaintListResponse,
    InsightComplaintRead,
    InsightComplaintSampleListResponse,
    InsightComplaintUpdate,
    InsightPreset,
    InsightProfileSnapshotListResponse,
    InsightRegionRiskMetricsListResponse,
    InsightAnalysisLogListResponse,
    InsightDecisionDashboard,
    InsightDecisionRecommendation,
    InsightDecisionSimulateRequest,
    InsightDecisionSimulateResult,
    InsightModelTrainResult,
    InsightNightlyJobAccepted,
    InsightSeedPreviewResult,
    InsightSeedResetResult,
    InsightSeedSamplesResult,
    InsightSeedStatus,
    InsightSeedPresetInfo,
    InsightSeedUsersResult,
    InsightSimulationWeightRead,
    InsightTouchpointListResponse,
    InsightUserProfileCreate,
    InsightUserProfileListResponse,
    InsightUserProfileRead,
    InsightUserProfileResponse,
    InsightUserProfileUpdate,
)

from app.services.modules.insight.decision_service import InsightDecisionService
from app.services.modules.insight.profile_service import InsightProfileService
from app.services.modules.insight.risk_snapshot_service import InsightRiskSnapshotService
from app.services.modules.insight.seed_service import InsightSeedService


router = APIRouter(prefix="/insight", tags=["insight"])


@router.get("/seed/status", response_model=InsightSeedStatus)
def insight_seed_status(
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据状态")),
) -> InsightSeedStatus:

    return service.get_status()


@router.get("/seed/presets", response_model=list[InsightSeedPresetInfo])
def insight_seed_presets(
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据状态")),
) -> list[InsightSeedPresetInfo]:

    return service.list_presets()


@router.post("/seed/users", response_model=InsightSeedUsersResult)
def insight_seed_users(
    preset: InsightPreset = Query(default="demo"),
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-customers", name="Insight 注入客户")),
) -> InsightSeedUsersResult:

    return service.seed_users(preset=preset)


@router.post("/seed/samples", response_model=InsightSeedSamplesResult)
def insight_seed_samples(
    preset: InsightPreset = Query(default="demo"),
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 注入样本")),
) -> InsightSeedSamplesResult:

    return service.seed_samples(preset=preset)


@router.post("/seed/reset-users", response_model=InsightSeedResetResult)
def insight_seed_reset_users(
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-customers", name="Insight 清空客户")),
) -> InsightSeedResetResult:

    return service.reset_users()


@router.post("/seed/reset-samples", response_model=InsightSeedResetResult)
def insight_seed_reset_samples(
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 清空样本")),
) -> InsightSeedResetResult:

    return service.reset_samples()


@router.get("/seed/preview", response_model=InsightSeedPreviewResult)
def insight_seed_preview(
    count: int = Query(default=3, ge=1, le=10),
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-preview", name="Insight 投诉预览")),
) -> InsightSeedPreviewResult:

    return service.preview_complaints(count=count)


@router.get("/users/{user_id}/profile", response_model=InsightUserProfileResponse)
def get_insight_user_profile(
    user_id: str,
    service: InsightProfileService = Depends(get_insight_profile_service),
    _: User = Depends(require_permission("91.profile", name="客户画像")),
) -> InsightUserProfileResponse:

    return service.get_profile(user_id)


@router.get("/users", response_model=InsightUserProfileListResponse)
def list_insight_users(
    user_id: str | None = Query(default=None),
    region: str | None = Query(default=None),
    age_group: str | None = Query(default=None),
    plan_id: str | None = Query(default=None),
    vip_level: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    age_min: int | None = Query(default=None, ge=0),
    age_max: int | None = Query(default=None, ge=0),
    has_sample: bool | None = Query(default=None, description="仅返回有/无样本的客户"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询")),
) -> InsightUserProfileListResponse:
    return insight_data.list_users(
        db,
        user_id=user_id,
        region=region,
        age_group=age_group,
        plan_id=plan_id,
        vip_level=vip_level,
        risk_level=risk_level,
        age_min=age_min,
        age_max=age_max,
        has_sample=has_sample,
        page=page,
        page_size=page_size,
    )


@router.post("/users", response_model=InsightUserProfileRead)
def create_insight_user(
    payload: InsightUserProfileCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-customers", name="Insight 用户维护")),
) -> InsightUserProfileRead:

    return insight_data.create_user(db, payload)


@router.put("/users/{user_id}", response_model=InsightUserProfileRead)
def update_insight_user(
    user_id: str,
    payload: InsightUserProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-customers", name="Insight 用户维护")),
) -> InsightUserProfileRead:

    return insight_data.update_user(db, user_id, payload)


@router.delete("/users/{user_id}")
def delete_insight_user(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-customers", name="Insight 用户维护")),
) -> dict[str, str]:

    insight_data.delete_user(db, user_id)

    return {"message": "ok"}


@router.get("/samples", response_model=InsightComplaintSampleListResponse)
def list_insight_samples(
    user_id: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询")),
) -> InsightComplaintSampleListResponse:
    return insight_data.list_complaint_samples(
        db, user_id=user_id, date_from=date_from, date_to=date_to, page=page, page_size=page_size
    )


@router.get("/touchpoints", response_model=InsightTouchpointListResponse)
def list_insight_touchpoints(
    user_id: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询")),
) -> InsightTouchpointListResponse:

    return insight_data.list_touchpoints(
        db, user_id=user_id, date_from=date_from, date_to=date_to, page=page, page_size=page_size
    )


@router.get("/complaint-categories", response_model=list[InsightComplaintCategoryPair])
def list_insight_complaint_categories(
    db: Session = Depends(get_db), _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询"))
) -> list[InsightComplaintCategoryPair]:

    return [InsightComplaintCategoryPair(**row) for row in insight_data.list_category_pairs(db)]


@router.get("/complaints", response_model=InsightComplaintListResponse)
def list_insight_complaints(
    user_id: str | None = Query(default=None),
    region: str | None = Query(default=None),
    main_category: str | None = Query(default=None),
    sub_category: str | None = Query(default=None),
    text_: str | None = Query(default=None, alias="text"),
    time_from: datetime | None = Query(default=None),
    time_to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询")),
) -> InsightComplaintListResponse:

    return insight_data.list_complaints(
        db,
        user_id=user_id,
        region=region,
        main_category=main_category,
        sub_category=sub_category,
        text_=text_,
        time_from=time_from,
        time_to=time_to,
        page=page,
        page_size=page_size,
    )


@router.post("/complaints", response_model=InsightComplaintRead)
def create_insight_complaint(
    payload: InsightComplaintCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 样本维护")),
) -> InsightComplaintRead:

    return insight_data.create_complaint(db, payload)


@router.put("/complaints/{complaint_id}", response_model=InsightComplaintRead)
def update_insight_complaint(
    complaint_id: str,
    payload: InsightComplaintUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 样本维护")),
) -> InsightComplaintRead:

    return insight_data.update_complaint(db, complaint_id, payload)


@router.delete("/complaints/{complaint_id}")
def delete_insight_complaint(
    complaint_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 样本维护")),
) -> dict[str, str]:

    insight_data.delete_complaint(db, complaint_id)

    return {"message": "ok"}


@router.get("/decision/dashboard", response_model=InsightDecisionDashboard)
def insight_decision_dashboard(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 决策看板")),
) -> InsightDecisionDashboard:
    return InsightDecisionService(db).dashboard()


@router.get("/decision/recommendations", response_model=list[InsightDecisionRecommendation])
def insight_decision_recommendations(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 决策推荐")),
) -> list[InsightDecisionRecommendation]:
    return InsightDecisionService(db).recommendations(limit=limit)


@router.post("/decision/simulate", response_model=InsightDecisionSimulateResult)
def insight_decision_simulate(
    payload: InsightDecisionSimulateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight WHAT-IF 仿真")),
) -> InsightDecisionSimulateResult:
    return InsightDecisionService(db).simulate(payload.user_id, payload.adjustments)


@router.post("/models/train", response_model=InsightModelTrainResult)
def insight_train_model(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 模型训练")),
) -> InsightModelTrainResult:
    version = InsightDecisionService(db).train_model()
    return InsightModelTrainResult(model_version=version)


@router.get("/simulation-weights", response_model=list[InsightSimulationWeightRead])
def list_insight_simulation_weights(
    db: Session = Depends(get_db), _: User = Depends(require_permission("91.seed-status", name="Insight 仿真配置"))
) -> list[InsightSimulationWeightRead]:

    return insight_data.list_simulation_weights(db)


@router.post("/jobs/nightly-run", response_model=InsightNightlyJobAccepted)
def run_insight_nightly_job(
    snapshot_date: date | None = Query(default=None),
    with_prev_day: bool = Query(default=False, description="同时构建前一日快照以生成环比（HF 建议关闭）"),
    mode: Literal["incremental", "full"] = Query(default="incremental", description="incremental=仅无分/无当日快照客户；full=全量"),
    service: InsightRiskSnapshotService = Depends(get_insight_risk_snapshot_service),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 深夜批处理")),
) -> InsightNightlyJobAccepted:
    return service.run_nightly(snapshot_date=snapshot_date, with_prev_day=with_prev_day, mode=mode)


@router.get("/jobs/logs", response_model=InsightAnalysisLogListResponse)
def list_insight_job_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 批处理日志")),
) -> InsightAnalysisLogListResponse:
    return insight_data.list_analysis_logs(db, page=page, page_size=page_size)


@router.post("/risk/build-snapshot", response_model=InsightNightlyJobAccepted)
def build_insight_risk_snapshot(
    snapshot_date: date | None = Query(default=None),
    with_prev_day: bool = Query(default=False, description="同时构建前一日快照以生成环比（HF 建议关闭）"),
    mode: Literal["incremental", "full"] = Query(default="incremental", description="incremental=仅无分/无当日快照客户；full=全量"),
    service: InsightRiskSnapshotService = Depends(get_insight_risk_snapshot_service),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 构建快照")),
) -> InsightNightlyJobAccepted:
    return service.build_snapshot(snapshot_date=snapshot_date, with_prev_day=with_prev_day, mode=mode)


@router.get("/snapshots", response_model=InsightProfileSnapshotListResponse)
def list_insight_snapshots(
    snapshot_date: date | None = Query(default=None),
    user_id: str | None = Query(default=None),
    region_l1: str | None = Query(default=None),
    region_l2: str | None = Query(default=None),
    churn_risk_level: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 快照查询")),
) -> InsightProfileSnapshotListResponse:
    return insight_data.list_snapshots(
        db,
        snapshot_date=snapshot_date,
        user_id=user_id,
        region_l1=region_l1,
        region_l2=region_l2,
        churn_risk_level=churn_risk_level,
        page=page,
        page_size=page_size,
    )


@router.get("/region-metrics", response_model=InsightRegionRiskMetricsListResponse)
def list_insight_region_metrics(
    snapshot_date: date | None = Query(default=None),
    region_l1: str | None = Query(default=None),
    region_l2: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 区域指标查询")),
) -> InsightRegionRiskMetricsListResponse:
    return insight_data.list_region_metrics(
        db,
        snapshot_date=snapshot_date,
        region_l1=region_l1,
        region_l2=region_l2,
        page=page,
        page_size=page_size,
    )
