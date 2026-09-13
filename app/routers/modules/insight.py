from datetime import date, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile

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
    InsightChurnLabelImportResult,
    InsightDecisionDashboard,
    InsightDecisionRecommendation,
    InsightDecisionSimulateRequest,
    InsightDecisionSimulateResult,
    InsightModelTrainResult,
    InsightNightlyJobAccepted,
    InsightSeedPreviewResult,
    InsightSeedPromoteSamplesResult,
    InsightSeedResetResult,
    InsightSeedSamplesResult,
    InsightSeedStatus,
    InsightSeedPresetInfo,
    InsightSeedUsersResult,
    InsightSimulationWeightRead,
    InsightSatisfactionEvalResponse,
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
    refresh: bool = Query(default=False, description="跳过缓存重新统计"),
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据状态")),
) -> InsightSeedStatus:
    return service.get_status(refresh=refresh)


@router.get("/seed/presets", response_model=list[InsightSeedPresetInfo])
def insight_seed_presets(
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据状态")),
) -> list[InsightSeedPresetInfo]:

    return service.list_presets()


@router.post("/seed/users", response_model=InsightSeedUsersResult)
def insight_seed_users(
    preset: InsightPreset = Query(default="demo"),
    count: int | None = Query(default=None, ge=1, le=500_000, description="指定追加条数；省略则按 preset 规模追加"),
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-customers", name="Insight 注入客户")),
) -> InsightSeedUsersResult:

    return service.seed_users(preset=preset, count=count)


@router.post("/seed/samples", response_model=InsightSeedSamplesResult)
def insight_seed_samples(
    preset: InsightPreset = Query(default="demo"),
    count: int | None = Query(default=None, ge=1, le=20_000, description="指定追加条数；省略则按 preset"),
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 注入样本")),
) -> InsightSeedSamplesResult:

    return service.seed_samples(preset=preset, count=count)


@router.post("/seed/promote-samples", response_model=InsightSeedPromoteSamplesResult)
def insight_seed_promote_samples(
    service: InsightSeedService = Depends(get_insight_seed_service),
    _: User = Depends(require_permission("91.seed-customers", name="Insight 合并样本到客户")),
) -> InsightSeedPromoteSamplesResult:

    return service.promote_samples()


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
    name: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    msisdn: str | None = Query(default=None),
    region: str | None = Query(default=None),
    region_l1: str | None = Query(default=None),
    region_l2: str | None = Query(default=None),
    age_group: str | None = Query(default=None),
    plan_id: str | None = Query(default=None),
    vip_level: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    device_brand: str | None = Query(default=None),
    network_type: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    age: int | None = Query(default=None, ge=0),
    age_min: int | None = Query(default=None, ge=0),
    age_max: int | None = Query(default=None, ge=0),
    join_date: date | None = Query(default=None),
    contract_end: date | None = Query(default=None),
    monthly_fee: float | None = Query(default=None),
    fee_drift_rate: float | None = Query(default=None),
    sample_id: int | None = Query(default=None, ge=1),
    satisfaction_net: int | None = Query(default=None, ge=1, le=5),
    satisfaction_srv: int | None = Query(default=None, ge=1, le=5),
    sample_satisfaction: float | None = Query(default=None),
    pred_satisfaction: float | None = Query(default=None),
    has_sample: bool | None = Query(default=None, description="仅返回有/无样本的客户"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询")),
) -> InsightUserProfileListResponse:
    return insight_data.list_users(
        db,
        user_id=user_id,
        name=name,
        gender=gender,
        msisdn=msisdn,
        region=region,
        region_l1=region_l1,
        region_l2=region_l2,
        age_group=age_group,
        plan_id=plan_id,
        vip_level=vip_level,
        channel=channel,
        device_brand=device_brand,
        network_type=network_type,
        risk_level=risk_level,
        age=age,
        age_min=age_min,
        age_max=age_max,
        join_date=join_date,
        contract_end=contract_end,
        monthly_fee=monthly_fee,
        fee_drift_rate=fee_drift_rate,
        sample_id=sample_id,
        satisfaction_net=satisfaction_net,
        satisfaction_srv=satisfaction_srv,
        sample_satisfaction=sample_satisfaction,
        pred_satisfaction=pred_satisfaction,
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
    sample_id: int | None = Query(default=None, ge=1),
    user_id: str | None = Query(default=None),
    name: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    msisdn: str | None = Query(default=None),
    age: int | None = Query(default=None, ge=0),
    region: str | None = Query(default=None),
    plan_id: str | None = Query(default=None),
    vip_level: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    device_brand: str | None = Query(default=None),
    network_type: str | None = Query(default=None),
    monthly_fee: float | None = Query(default=None),
    join_date: date | None = Query(default=None),
    contract_end: date | None = Query(default=None),
    fee_drift_rate: float | None = Query(default=None),
    satisfaction_net: int | None = Query(default=None, ge=1, le=5),
    satisfaction_srv: int | None = Query(default=None, ge=1, le=5),
    satisfaction_score: float | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询")),
) -> InsightComplaintSampleListResponse:
    return insight_data.list_complaint_samples(
        db,
        sample_id=sample_id,
        user_id=user_id,
        name=name,
        gender=gender,
        msisdn=msisdn,
        age=age,
        region=region,
        plan_id=plan_id,
        vip_level=vip_level,
        channel=channel,
        device_brand=device_brand,
        network_type=network_type,
        monthly_fee=monthly_fee,
        join_date=join_date,
        contract_end=contract_end,
        fee_drift_rate=fee_drift_rate,
        satisfaction_net=satisfaction_net,
        satisfaction_srv=satisfaction_srv,
        satisfaction_score=satisfaction_score,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )


@router.get("/touchpoints", response_model=InsightTouchpointListResponse)
def list_insight_touchpoints(
    user_id: str | None = Query(default=None),
    name: str | None = Query(default=None),
    gender: str | None = Query(default=None),
    msisdn: str | None = Query(default=None),
    age: int | None = Query(default=None, ge=0),
    region: str | None = Query(default=None),
    plan_id: str | None = Query(default=None),
    vip_level: str | None = Query(default=None),
    channel: str | None = Query(default=None),
    device_brand: str | None = Query(default=None),
    network_type: str | None = Query(default=None),
    monthly_fee: float | None = Query(default=None),
    join_date: date | None = Query(default=None),
    contract_end: date | None = Query(default=None),
    fee_drift_rate: float | None = Query(default=None),
    satisfaction_net: int | None = Query(default=None, ge=1, le=5),
    satisfaction_srv: int | None = Query(default=None, ge=1, le=5),
    satisfaction_score: float | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 数据查询")),
) -> InsightTouchpointListResponse:

    return insight_data.list_touchpoints(
        db,
        user_id=user_id,
        name=name,
        gender=gender,
        msisdn=msisdn,
        age=age,
        region=region,
        plan_id=plan_id,
        vip_level=vip_level,
        channel=channel,
        device_brand=device_brand,
        network_type=network_type,
        monthly_fee=monthly_fee,
        join_date=join_date,
        contract_end=contract_end,
        fee_drift_rate=fee_drift_rate,
        satisfaction_net=satisfaction_net,
        satisfaction_srv=satisfaction_srv,
        satisfaction_score=satisfaction_score,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
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
    refresh: bool = Query(default=False, description="跳过缓存重新统计"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 决策看板")),
) -> InsightDecisionDashboard:
    return InsightDecisionService(db).dashboard(refresh=refresh)


@router.get("/eval/satisfaction", response_model=InsightSatisfactionEvalResponse)
def insight_eval_satisfaction(
    limit_examples: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 满意度评估")),
) -> InsightSatisfactionEvalResponse:
    from app.services.modules.insight.satisfaction_eval import evaluate_satisfaction

    return evaluate_satisfaction(db, limit_examples=limit_examples)


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
    return InsightDecisionService(db).train_model()


@router.post("/churn-labels/import", response_model=InsightChurnLabelImportResult)
async def insight_import_churn_labels(
    file: UploadFile = File(..., description="UTF-8 CSV：user_id,as_of_date,churn_90d 或 user_id,cancel_date"),
    as_of_date: date | None = Query(default=None, description="仅 cancel_date 格式时必填"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 导入流失标签")),
) -> InsightChurnLabelImportResult:
    raw = await file.read()
    return InsightDecisionService(db).import_churn_labels(raw, as_of_date=as_of_date)


@router.delete("/churn-labels")
def insight_clear_churn_labels(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-samples", name="Insight 清空流失标签")),
) -> dict[str, int]:
    return InsightDecisionService(db).clear_churn_labels()


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
    refresh: bool = Query(default=False, description="跳过缓存重新查询"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("91.seed-status", name="Insight 区域指标查询")),
) -> InsightRegionRiskMetricsListResponse:
    from app.services.modules.insight.stats_cache import (
        get_cached_region_metrics,
        set_cached_region_metrics,
    )

    cache_kwargs: dict[str, Any] = dict(
        snapshot_date=snapshot_date,
        region_l1=region_l1,
        region_l2=region_l2,
        page=page,
        page_size=page_size,
    )
    if not refresh:
        cached = get_cached_region_metrics(**cache_kwargs)
        if cached is not None:
            return cached
    result = insight_data.list_region_metrics(
        db,
        snapshot_date=snapshot_date,
        region_l1=region_l1,
        region_l2=region_l2,
        page=page,
        page_size=page_size,
    )
    set_cached_region_metrics(**cache_kwargs, result=result)
    return result
