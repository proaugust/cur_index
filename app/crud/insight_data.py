"""Insight 数据管理 CRUD。"""

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud import insight as crud_insight
from app.models.insight import (
    CfgSimulationWeight,
    DimUserProfile,
    DimUserProfileSnapshot,
    FactComplaintSample,
    FactRegionRiskMetrics,
    InsightAnalysisLog,
)
from app.schemas.insight import (
    InsightAnalysisLogListResponse,
    InsightAnalysisLogRead,
    InsightComplaintCreate,
    InsightComplaintListResponse,
    InsightComplaintRead,
    InsightComplaintSampleListResponse,
    InsightComplaintSampleRead,
    InsightComplaintUpdate,
    InsightProfileSnapshotListResponse,
    InsightProfileSnapshotRead,
    InsightRegionRiskMetricsListResponse,
    InsightRegionRiskMetricsRead,
    InsightSimulationWeightRead,
    InsightTouchpointListResponse,
    InsightUserProfileCreate,
    InsightUserProfileListItem,
    InsightUserProfileListResponse,
    InsightUserProfileRead,
    InsightUserProfileUpdate,
)
from app.services.modules.insight.vector_service import embed_complaint_text


def _page(query, page: int, page_size: int):
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def _get_or_404(db: Session, model, pk, label: str):
    row = db.get(model, pk)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label}不存在")
    return row


def list_users(
    db: Session,
    *,
    user_id: str | None = None,
    region: str | None = None,
    region_l1: str | None = None,
    region_l2: str | None = None,
    age_group: str | None = None,
    plan_id: str | None = None,
    vip_level: str | None = None,
    risk_level: str | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    has_sample: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightUserProfileListResponse:
    sample_stats = (
        db.query(
            FactComplaintSample.user_id.label("user_id"),
            func.count(FactComplaintSample.sample_id).label("sample_count"),
            func.count(FactComplaintSample.complaint_id).label("complaint_count"),
        )
        .group_by(FactComplaintSample.user_id)
        .subquery()
    )
    # 风险分在快照表；取每个用户最新一天快照覆盖列表展示
    ranked_snap = (
        db.query(
            DimUserProfileSnapshot.user_id.label("user_id"),
            DimUserProfileSnapshot.risk_score.label("risk_score"),
            DimUserProfileSnapshot.churn_risk_level.label("risk_level"),
            DimUserProfileSnapshot.tags.label("tags"),
            DimUserProfileSnapshot.shap_values.label("shap_values"),
            func.row_number()
            .over(
                partition_by=DimUserProfileSnapshot.user_id,
                order_by=DimUserProfileSnapshot.snapshot_date.desc(),
            )
            .label("rn"),
        )
    ).subquery()
    latest_snap = db.query(ranked_snap).filter(ranked_snap.c.rn == 1).subquery()

    query = (
        db.query(
            DimUserProfile,
            func.coalesce(sample_stats.c.sample_count, 0).label("sample_count"),
            func.coalesce(sample_stats.c.complaint_count, 0).label("complaint_count"),
            latest_snap.c.risk_score.label("snap_risk_score"),
            latest_snap.c.risk_level.label("snap_risk_level"),
            latest_snap.c.tags.label("snap_tags"),
            latest_snap.c.shap_values.label("snap_shap_values"),
        )
        .outerjoin(sample_stats, DimUserProfile.user_id == sample_stats.c.user_id)
        .outerjoin(latest_snap, DimUserProfile.user_id == latest_snap.c.user_id)
    )
    if user_id:
        query = query.filter(DimUserProfile.user_id == user_id)
    for column, value in (
        (DimUserProfile.region, region),
        (DimUserProfile.region_l1, region_l1),
        (DimUserProfile.region_l2, region_l2),
        (DimUserProfile.age_group, age_group),
        (DimUserProfile.plan_id, plan_id),
        (DimUserProfile.vip_level, vip_level),
    ):
        if value:
            query = query.filter(column.ilike(f"%{value}%"))
    if risk_level:
        query = query.filter(
            func.coalesce(latest_snap.c.risk_level, DimUserProfile.risk_level).ilike(f"%{risk_level}%")
        )
    if age_min is not None:
        query = query.filter(DimUserProfile.age >= age_min)
    if age_max is not None:
        query = query.filter(DimUserProfile.age <= age_max)
    if has_sample is True:
        query = query.filter(func.coalesce(sample_stats.c.sample_count, 0) > 0)
    elif has_sample is False:
        query = query.filter(func.coalesce(sample_stats.c.sample_count, 0) == 0)
    rows, total = _page(query.order_by(DimUserProfile.user_id.desc()), page, page_size)
    items = []
    for profile, sample_count, complaint_count, snap_risk, snap_level, snap_tags, snap_shap in rows:
        item = InsightUserProfileListItem.model_validate(profile).model_copy(
            update={
                "sample_count": int(sample_count),
                "complaint_count": int(complaint_count),
                "risk_score": snap_risk if snap_risk is not None else profile.risk_score,
                "risk_level": snap_level if snap_level is not None else profile.risk_level,
                "tags": snap_tags if snap_tags is not None else profile.tags,
                "shap_values": snap_shap if snap_shap is not None else profile.shap_values,
            }
        )
        items.append(item)
    return InsightUserProfileListResponse(list=items, pageTotal=total)


def create_user(db: Session, payload: InsightUserProfileCreate) -> InsightUserProfileRead:
    if db.get(DimUserProfile, payload.user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户 ID 已存在")
    row = DimUserProfile(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return InsightUserProfileRead.model_validate(row)


def update_user(db: Session, user_id: str, payload: InsightUserProfileUpdate) -> InsightUserProfileRead:
    row = _get_or_404(db, DimUserProfile, user_id, "用户")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return InsightUserProfileRead.model_validate(row)


def delete_user(db: Session, user_id: str) -> None:
    row = _get_or_404(db, DimUserProfile, user_id, "用户")
    db.delete(row)
    db.commit()


def list_complaint_samples(
    db: Session,
    *,
    user_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightComplaintSampleListResponse:
    query = db.query(FactComplaintSample)
    if user_id:
        query = query.filter(FactComplaintSample.user_id == user_id)
    if date_from:
        query = query.filter(FactComplaintSample.record_date >= date_from)
    if date_to:
        query = query.filter(FactComplaintSample.record_date <= date_to)
    rows, total = _page(
        query.order_by(FactComplaintSample.record_date.desc(), FactComplaintSample.sample_id.desc()),
        page,
        page_size,
    )
    return InsightComplaintSampleListResponse(
        list=[InsightComplaintSampleRead.model_validate(row) for row in rows],
        pageTotal=total,
    )


def list_touchpoints(
    db: Session,
    *,
    user_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightTouchpointListResponse:
    return list_complaint_samples(
        db, user_id=user_id, date_from=date_from, date_to=date_to, page=page, page_size=page_size
    )


def list_category_pairs(db: Session) -> list[dict]:
    return crud_insight.list_category_pairs()


def _complaint_read(row: FactComplaintSample, region: str | None = None) -> InsightComplaintRead:
    data = InsightComplaintRead.model_validate(row).model_dump()
    data["region"] = region
    return InsightComplaintRead(**data)


def list_complaints(
    db: Session,
    *,
    user_id: str | None = None,
    region: str | None = None,
    main_category: str | None = None,
    sub_category: str | None = None,
    complaint_type: str | None = None,
    text_: str | None = None,
    time_from: datetime | None = None,
    time_to: datetime | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightComplaintListResponse:
    query = (
        db.query(FactComplaintSample, DimUserProfile.region)
        .outerjoin(DimUserProfile, FactComplaintSample.user_id == DimUserProfile.user_id)
        .filter(FactComplaintSample.complaint_id.isnot(None))
    )
    if user_id:
        query = query.filter(FactComplaintSample.user_id == user_id)
    if region:
        query = query.filter(DimUserProfile.region.ilike(f"%{region}%"))
    type_filter = complaint_type or main_category
    for column, value in (
        (FactComplaintSample.complaint_type, type_filter),
        (FactComplaintSample.sub_category, sub_category),
    ):
        if value:
            query = query.filter(column == value)
    if text_:
        query = query.filter(FactComplaintSample.raw_text.ilike(f"%{text_}%"))
    if time_from:
        query = query.filter(FactComplaintSample.sample_time >= time_from)
    if time_to:
        query = query.filter(FactComplaintSample.sample_time <= time_to)
    rows, total = _page(
        query.order_by(
            FactComplaintSample.sample_time.desc(),
            FactComplaintSample.complaint_id.desc(),
        ),
        page,
        page_size,
    )
    return InsightComplaintListResponse(list=[_complaint_read(row[0], row[1]) for row in rows], pageTotal=total)


def create_complaint(db: Session, payload: InsightComplaintCreate) -> InsightComplaintRead:
    data = payload.model_dump()
    if not data.get("complaint_id"):
        complaint_count = crud_insight.get_seed_status(db)["complaints"]
        data["complaint_id"] = f"C{payload.sample_time.strftime('%Y%m%d')}{complaint_count + 1:05d}"
    data["record_date"] = data.get("record_date") or payload.sample_time.date()
    data["survey_answers"] = data.get("survey_answers") or []
    data["survey_category_scores"] = data.get("survey_category_scores") or {}
    data["satisfaction_score"] = data.get("satisfaction_score") or 0
    data["complaint_vector"] = embed_complaint_text(data["raw_text"])
    row = FactComplaintSample(**data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _complaint_read(row)


def update_complaint(db: Session, complaint_id: str, payload: InsightComplaintUpdate) -> InsightComplaintRead:
    row = (
        db.query(FactComplaintSample)
        .filter(FactComplaintSample.complaint_id == complaint_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投诉不存在")
    data = payload.model_dump(exclude_unset=True)
    if "sample_time" in data and "record_date" not in data and data["sample_time"]:
        data["record_date"] = data["sample_time"].date()
    if data.get("raw_text"):
        data["complaint_vector"] = embed_complaint_text(data["raw_text"])
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _complaint_read(row)


def delete_complaint(db: Session, complaint_id: str) -> None:
    row = (
        db.query(FactComplaintSample)
        .filter(FactComplaintSample.complaint_id == complaint_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="投诉不存在")
    db.delete(row)
    db.commit()


def list_snapshots(
    db: Session,
    *,
    snapshot_date: date | None = None,
    user_id: str | None = None,
    region_l1: str | None = None,
    region_l2: str | None = None,
    churn_risk_level: str | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightProfileSnapshotListResponse:
    query = db.query(DimUserProfileSnapshot)
    if snapshot_date:
        query = query.filter(DimUserProfileSnapshot.snapshot_date == snapshot_date)
    if user_id:
        query = query.filter(DimUserProfileSnapshot.user_id == user_id)
    for column, value in (
        (DimUserProfileSnapshot.region_l1, region_l1),
        (DimUserProfileSnapshot.region_l2, region_l2),
        (DimUserProfileSnapshot.churn_risk_level, churn_risk_level),
    ):
        if value:
            query = query.filter(column.ilike(f"%{value}%"))
    rows, total = _page(
        query.order_by(
            DimUserProfileSnapshot.snapshot_date.desc(),
            DimUserProfileSnapshot.risk_score.desc(),
        ),
        page,
        page_size,
    )
    return InsightProfileSnapshotListResponse(
        list=[InsightProfileSnapshotRead.model_validate(row) for row in rows],
        pageTotal=total,
    )


def list_region_metrics(
    db: Session,
    *,
    snapshot_date: date | None = None,
    region_l1: str | None = None,
    region_l2: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> InsightRegionRiskMetricsListResponse:
    query = db.query(FactRegionRiskMetrics)
    if snapshot_date:
        query = query.filter(FactRegionRiskMetrics.snapshot_date == snapshot_date)
    for column, value in (
        (FactRegionRiskMetrics.region_l1, region_l1),
        (FactRegionRiskMetrics.region_l2, region_l2),
    ):
        if value:
            query = query.filter(column.ilike(f"%{value}%"))
    rows, total = _page(
        query.order_by(
            FactRegionRiskMetrics.snapshot_date.desc(),
            FactRegionRiskMetrics.high_risk_ratio.desc(),
        ),
        page,
        page_size,
    )
    return InsightRegionRiskMetricsListResponse(
        list=[InsightRegionRiskMetricsRead.model_validate(row) for row in rows],
        pageTotal=total,
    )


def list_analysis_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 10,
) -> InsightAnalysisLogListResponse:
    query = db.query(InsightAnalysisLog).filter(InsightAnalysisLog.question == "insight-nightly-risk-pipeline")
    rows, total = _page(query.order_by(InsightAnalysisLog.created_at.desc()), page, page_size)
    return InsightAnalysisLogListResponse(
        list=[InsightAnalysisLogRead.model_validate(row) for row in rows],
        pageTotal=total,
    )


def list_simulation_weights(db: Session) -> list[InsightSimulationWeightRead]:
    rows = db.query(CfgSimulationWeight).order_by(CfgSimulationWeight.base_importance.desc()).all()
    return [InsightSimulationWeightRead.model_validate(row) for row in rows]
