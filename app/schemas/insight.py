"""Insight 模块请求/响应模型。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

InsightPreset = Literal["mini", "dev", "demo", "full"]


class InsightSeedPresetInfo(BaseModel):
    key: InsightPreset
    users: int
    complaints: int
    touchpoints: int


class InsightSeedStatus(BaseModel):
    users: int = 0
    complaints: int = 0
    touchpoints: int = 0
    samples: int = 0
    snapshots: int = 0
    region_metrics: int = 0
    simulation_weights: int = 0
    analysis_logs: int = 0


class InsightSeedUsersResult(BaseModel):
    preset: InsightPreset
    inserted: int
    elapsed_ms: int


class InsightSeedSamplesResult(BaseModel):
    preset: InsightPreset
    complaints_inserted: int
    touchpoints_inserted: int
    samples_inserted: int
    elapsed_ms: int


class InsightSeedResetResult(BaseModel):
    cleared: dict[str, int]


class InsightComplaintPreview(BaseModel):
    main_category: str
    sub_category: str
    raw_text: str


class InsightSeedPreviewResult(BaseModel):
    items: list[InsightComplaintPreview]


class InsightUserProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    age: int = Field(ge=0, le=120)
    age_group: str = Field(min_length=1, max_length=20)
    region_l1: str = Field(min_length=1, max_length=30)
    region_l2: str = Field(min_length=1, max_length=30)
    region: str = Field(min_length=1, max_length=50)
    plan_id: str = Field(min_length=1, max_length=20)
    vip_level: str = Field(default="普通", max_length=20)
    join_date: date
    monthly_fee: Decimal = Field(default=Decimal("0"), ge=0)
    fee_drift_rate: Decimal = Field(default=Decimal("0"))
    satisfaction_net: int | None = Field(default=None, ge=1, le=5)
    satisfaction_srv: int | None = Field(default=None, ge=1, le=5)
    risk_score: Decimal | None = Field(default=None, ge=0, le=1)
    risk_level: str | None = Field(default=None, max_length=10)
    tags: list[str] | None = None
    shap_values: dict[str, Any] | None = None


class InsightUserProfileCreate(InsightUserProfileBase):
    user_id: str = Field(min_length=1, max_length=32)


class InsightUserProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    age: int | None = Field(default=None, ge=0, le=120)
    age_group: str | None = Field(default=None, max_length=20)
    region_l1: str | None = Field(default=None, max_length=30)
    region_l2: str | None = Field(default=None, max_length=30)
    region: str | None = Field(default=None, max_length=50)
    plan_id: str | None = Field(default=None, max_length=20)
    vip_level: str | None = Field(default=None, max_length=20)
    join_date: date | None = None
    monthly_fee: Decimal | None = Field(default=None, ge=0)
    fee_drift_rate: Decimal | None = None
    satisfaction_net: int | None = Field(default=None, ge=1, le=5)
    satisfaction_srv: int | None = Field(default=None, ge=1, le=5)
    risk_score: Decimal | None = Field(default=None, ge=0, le=1)
    risk_level: str | None = Field(default=None, max_length=10)
    tags: list[str] | None = None
    shap_values: dict[str, Any] | None = None


class InsightUserProfileRead(InsightUserProfileBase):
    user_id: str

    model_config = {"from_attributes": True}


class InsightUserProfileListItem(InsightUserProfileRead):
    sample_count: int = 0
    complaint_count: int = 0


class InsightUserProfileListResponse(BaseModel):
    list: list[InsightUserProfileListItem]
    pageTotal: int


class InsightComplaintBase(BaseModel):
    user_id: str = Field(min_length=1, max_length=32)
    sample_time: datetime
    complaint_type: str = Field(min_length=1, max_length=50)
    sub_category: str = Field(min_length=1, max_length=50)
    raw_text: str = Field(min_length=1)
    record_date: date | None = None
    survey_answers: list[dict[str, Any]] | None = None
    survey_category_scores: dict[str, Any] | None = None
    satisfaction_score: Decimal | None = Field(default=None, ge=0, le=5)


class InsightComplaintCreate(InsightComplaintBase):
    complaint_id: str | None = Field(default=None, max_length=32)


class InsightComplaintUpdate(BaseModel):
    user_id: str | None = Field(default=None, max_length=32)
    sample_time: datetime | None = None
    complaint_type: str | None = Field(default=None, max_length=50)
    sub_category: str | None = Field(default=None, max_length=50)
    raw_text: str | None = Field(default=None, min_length=1)
    record_date: date | None = None
    survey_answers: list[dict[str, Any]] | None = None
    survey_category_scores: dict[str, Any] | None = None
    satisfaction_score: Decimal | None = Field(default=None, ge=0, le=5)


class InsightComplaintRead(InsightComplaintBase):
    complaint_id: str
    complaint_vector: list[float] | None = None
    region: str | None = None

    model_config = {"from_attributes": True}


class InsightComplaintListResponse(BaseModel):
    list: list[InsightComplaintRead]
    pageTotal: int


class InsightComplaintCategoryPair(BaseModel):
    main_category: str
    sub_category: str


class InsightComplaintSampleRead(BaseModel):
    sample_id: int
    user_id: str
    sample_time: datetime
    record_date: date
    survey_answers: list[dict[str, Any]]
    survey_category_scores: dict[str, Any]
    satisfaction_score: Decimal
    complaint_id: str | None = None
    complaint_type: str | None = None
    sub_category: str | None = None
    raw_text: str | None = None
    complaint_vector: list[float] | None = None

    model_config = {"from_attributes": True}


class InsightComplaintSampleListResponse(BaseModel):
    list: list[InsightComplaintSampleRead]
    pageTotal: int


InsightTouchpointRead = InsightComplaintSampleRead
InsightTouchpointListResponse = InsightComplaintSampleListResponse


class InsightProfileSnapshotRead(BaseModel):
    snapshot_date: date
    user_id: str
    region_l1: str
    region_l2: str
    age_group: str
    plan_id: str
    vip_level: str
    churn_risk_level: str
    activity_trend: str
    risk_score: Decimal
    tags: list[str] | None = None
    shap_values: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class InsightProfileSnapshotListResponse(BaseModel):
    list: list[InsightProfileSnapshotRead]
    pageTotal: int


class InsightRegionRiskMetricsRead(BaseModel):
    snapshot_date: date
    region_l1: str
    region_l2: str
    total_customers: int
    high_risk_ratio: Decimal
    risk_ratio_mom: Decimal

    model_config = {"from_attributes": True}


class InsightRegionRiskMetricsListResponse(BaseModel):
    list: list[InsightRegionRiskMetricsRead]
    pageTotal: int


class InsightRiskBuildResult(BaseModel):
    snapshot_date: date
    snapshots_upserted: int
    region_metrics_upserted: int
    elapsed_ms: int
    mode: Literal["incremental", "full"] = "incremental"
    prev_snapshot_date: date | None = None
    prev_snapshots_upserted: int = 0
    prev_region_metrics_upserted: int = 0


class InsightPipelineStepResult(BaseModel):
    step: Literal["ai_risk_engine", "snapshot_writer", "region_aggregator"]
    label: str
    output_count: int
    elapsed_ms: int


class InsightNightlyRunResult(BaseModel):
    snapshot_date: date
    steps: list[InsightPipelineStepResult]
    snapshots_upserted: int
    region_metrics_upserted: int
    analysis_log_id: int
    elapsed_ms: int
    model_version: str
    mode: Literal["incremental", "full"] = "incremental"
    prev_snapshot_date: date | None = None
    prev_snapshots_upserted: int = 0
    prev_region_metrics_upserted: int = 0


class InsightNightlyJobAccepted(BaseModel):
    """后台批处理已受理，前端轮询 /jobs/logs 至 completed/failed。"""

    analysis_log_id: int
    snapshot_date: date
    mode: Literal["incremental", "full"]
    status: Literal["accepted"] = "accepted"
    pending_users: int
    message: str = "批处理已在后台启动，请刷新日志查看进度"


class InsightAnalysisLogRead(BaseModel):
    id: int
    question: str
    answer: str | None = None
    status: str
    tools_trace: dict[str, Any] | None = None
    latency_ms: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InsightAnalysisLogListResponse(BaseModel):
    list: list[InsightAnalysisLogRead]
    pageTotal: int


class InsightSimulationWeightRead(BaseModel):
    feature_name: str
    base_importance: Decimal
    impact_coefficient: Decimal

    model_config = {"from_attributes": True}


class InsightModelTrainResult(BaseModel):
    model_version: str
    message: str = "训练完成"


class InsightDecisionDashboard(BaseModel):
    model_version: str
    has_trained_model: bool
    latest_snapshot_date: date | None = None
    snapshot_total: int = 0
    high_risk_total: int = 0
    simulation_weights: list[InsightSimulationWeightRead] = Field(default_factory=list)


class InsightDecisionRecommendation(BaseModel):
    user_id: str
    name: str
    risk_score: Decimal
    churn_risk_level: str
    tags: list[str] = Field(default_factory=list)
    top_shap: dict[str, float] = Field(default_factory=dict)
    suggested_action: str


class InsightDecisionSimulateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=32)
    adjustments: dict[str, float] = Field(default_factory=dict)


class InsightDecisionSimulateResult(BaseModel):
    user_id: str
    baseline_risk: Decimal
    scenario_risk: Decimal
    delta_risk: Decimal
    baseline_level: str
    scenario_level: str
    adjustments: dict[str, float]


class InsightProfileStats(BaseModel):
    complaint_total: int
    touchpoint_total: int
    sample_total: int
    latest_complaint_time: datetime | None = None
    latest_touchpoint_date: date | None = None
    latest_sample_time: datetime | None = None


class InsightProfileCacheMeta(BaseModel):
    hit: bool = False
    hot: bool = False
    source: Literal["redis", "memory", "db"] = "db"
    ttl_seconds: int | None = None


class InsightUserProfileResponse(BaseModel):
    profile: InsightUserProfileRead
    stats: InsightProfileStats
    recent_complaints: list[InsightComplaintRead]
    recent_touchpoints: list[InsightTouchpointRead]
    recent_samples: list[InsightComplaintSampleRead]
    snapshot: InsightProfileSnapshotRead | None = None
    cache: InsightProfileCacheMeta = Field(default_factory=InsightProfileCacheMeta)
