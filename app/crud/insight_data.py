"""Insight 数据管理 CRUD。"""

from datetime import date, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, inspect as sa_inspect, or_
from sqlalchemy.orm import Session, defer

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

_DEFER_COMPLAINT_VECTOR = defer(FactComplaintSample.complaint_vector, raiseload=True)


def _orm_columns_dict(row) -> dict:
    """ORM 列字典；deferred/unloaded 列填 None，避免触达触发二次查询。"""
    state = sa_inspect(row)
    out: dict = {}
    for attr in state.mapper.column_attrs:
        key = attr.key
        out[key] = None if key in state.unloaded else getattr(row, key)
    return out


def _page(query, page: int, page_size: int):
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return rows, total


def _get_or_404(db: Session, model, pk, label: str):
    row = db.get(model, pk)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label}不存在")
    return row


def _sample_counts_for_users(db: Session, user_ids: list[str]) -> dict[str, tuple[int, int]]:
    if not user_ids:
        return {}
    rows = (
        db.query(
            FactComplaintSample.user_id,
            func.count(FactComplaintSample.sample_id),
            func.count(FactComplaintSample.complaint_id),
        )
        .filter(FactComplaintSample.user_id.in_(user_ids))
        .group_by(FactComplaintSample.user_id)
        .all()
    )
    return {uid: (int(sc), int(cc)) for uid, sc, cc in rows}


def _latest_snaps_for_users(db: Session, user_ids: list[str]) -> dict[str, DimUserProfileSnapshot]:
    if not user_ids:
        return {}
    max_dates = (
        db.query(
            DimUserProfileSnapshot.user_id.label("user_id"),
            func.max(DimUserProfileSnapshot.snapshot_date).label("max_date"),
        )
        .filter(DimUserProfileSnapshot.user_id.in_(user_ids))
        .group_by(DimUserProfileSnapshot.user_id)
        .subquery()
    )
    rows = (
        db.query(DimUserProfileSnapshot)
        .join(
            max_dates,
            (DimUserProfileSnapshot.user_id == max_dates.c.user_id)
            & (DimUserProfileSnapshot.snapshot_date == max_dates.c.max_date),
        )
        .all()
    )
    return {row.user_id: row for row in rows}


def list_users(
    db: Session,
    *,
    user_id: str | None = None,
    name: str | None = None,
    gender: str | None = None,
    msisdn: str | None = None,
    region: str | None = None,
    region_l1: str | None = None,
    region_l2: str | None = None,
    age_group: str | None = None,
    plan_id: str | None = None,
    vip_level: str | None = None,
    channel: str | None = None,
    device_brand: str | None = None,
    network_type: str | None = None,
    risk_level: str | None = None,
    age: int | None = None,
    age_min: int | None = None,
    age_max: int | None = None,
    join_date: date | None = None,
    contract_end: date | None = None,
    monthly_fee: float | None = None,
    fee_drift_rate: float | None = None,
    sample_id: int | None = None,
    satisfaction_net: int | None = None,
    satisfaction_srv: int | None = None,
    sample_satisfaction: float | None = None,
    pred_satisfaction: float | None = None,
    has_sample: bool | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightUserProfileListResponse:
    # 先对主表过滤分页，再仅对当前页聚合样本/最新快照（避免全表 GROUP BY + 窗口）
    query = db.query(DimUserProfile)
    if user_id:
        query = query.filter(DimUserProfile.user_id == user_id)
    if name:
        query = query.filter(DimUserProfile.name.ilike(f"%{name}%"))
    if msisdn:
        query = query.filter(DimUserProfile.msisdn.ilike(f"%{msisdn}%"))
    if device_brand:
        query = query.filter(DimUserProfile.device_brand.ilike(f"%{device_brand}%"))
    for column, value in (
        (DimUserProfile.region, region),
        (DimUserProfile.region_l1, region_l1),
        (DimUserProfile.region_l2, region_l2),
    ):
        if value:
            query = query.filter(column.ilike(f"{value}%"))
    for column, value in (
        (DimUserProfile.gender, gender),
        (DimUserProfile.age_group, age_group),
        (DimUserProfile.plan_id, plan_id),
        (DimUserProfile.vip_level, vip_level),
        (DimUserProfile.channel, channel),
        (DimUserProfile.network_type, network_type),
    ):
        if value:
            query = query.filter(column == value)
    if age is not None:
        query = query.filter(DimUserProfile.age == age)
    if age_min is not None:
        query = query.filter(DimUserProfile.age >= age_min)
    if age_max is not None:
        query = query.filter(DimUserProfile.age <= age_max)
    if join_date is not None:
        query = query.filter(DimUserProfile.join_date == join_date)
    if contract_end is not None:
        query = query.filter(DimUserProfile.contract_end == contract_end)
    if monthly_fee is not None:
        query = query.filter(DimUserProfile.monthly_fee == monthly_fee)
    if fee_drift_rate is not None:
        query = query.filter(DimUserProfile.fee_drift_rate == fee_drift_rate)
    if sample_id is not None:
        query = query.filter(
            db.query(FactComplaintSample.sample_id)
            .filter(
                FactComplaintSample.user_id == DimUserProfile.user_id,
                FactComplaintSample.sample_id == sample_id,
            )
            .exists()
        )
    if satisfaction_net is not None:
        query = query.filter(DimUserProfile.satisfaction_net == satisfaction_net)
    if satisfaction_srv is not None:
        query = query.filter(DimUserProfile.satisfaction_srv == satisfaction_srv)
    if sample_satisfaction is not None:
        query = query.filter(DimUserProfile.sample_satisfaction == sample_satisfaction)
    if pred_satisfaction is not None:
        query = query.filter(DimUserProfile.pred_satisfaction == pred_satisfaction)
    sample_exists = (
        db.query(FactComplaintSample.sample_id)
        .filter(FactComplaintSample.user_id == DimUserProfile.user_id)
        .exists()
    )
    if has_sample is True:
        query = query.filter(sample_exists)
    elif has_sample is False:
        query = query.filter(~sample_exists)
    # 夜间快照会回写 profile.risk_level；按主表等值过滤，避免全表窗口 join
    if risk_level:
        query = query.filter(DimUserProfile.risk_level == risk_level)
    profiles, total = _page(query.order_by(DimUserProfile.user_id.desc()), page, page_size)
    page_ids = [p.user_id for p in profiles]
    counts = _sample_counts_for_users(db, page_ids)
    snaps = _latest_snaps_for_users(db, page_ids)
    items = []
    for profile in profiles:
        sample_count, complaint_count = counts.get(profile.user_id, (0, 0))
        snap = snaps.get(profile.user_id)
        item = InsightUserProfileListItem.model_validate(profile).model_copy(
            update={
                "sample_count": sample_count,
                "complaint_count": complaint_count,
                "risk_score": snap.risk_score if snap is not None else profile.risk_score,
                "risk_level": snap.churn_risk_level if snap is not None else profile.risk_level,
                "tags": snap.tags if snap is not None else profile.tags,
                "shap_values": snap.shap_values if snap is not None else profile.shap_values,
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
    sample_id: int | None = None,
    user_id: str | None = None,
    name: str | None = None,
    gender: str | None = None,
    msisdn: str | None = None,
    age: int | None = None,
    region: str | None = None,
    plan_id: str | None = None,
    vip_level: str | None = None,
    channel: str | None = None,
    device_brand: str | None = None,
    network_type: str | None = None,
    monthly_fee: float | None = None,
    join_date: date | None = None,
    contract_end: date | None = None,
    fee_drift_rate: float | None = None,
    satisfaction_net: int | None = None,
    satisfaction_srv: int | None = None,
    satisfaction_score: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightComplaintSampleListResponse:
    query = db.query(FactComplaintSample).options(_DEFER_COMPLAINT_VECTOR)
    if sample_id is not None:
        query = query.filter(FactComplaintSample.sample_id == sample_id)
    if user_id:
        query = query.filter(FactComplaintSample.user_id == user_id)
    if name:
        query = query.filter(FactComplaintSample.name.ilike(f"%{name}%"))
    if msisdn:
        query = query.filter(FactComplaintSample.msisdn.ilike(f"%{msisdn}%"))
    if region:
        query = query.filter(FactComplaintSample.region.ilike(f"%{region}%"))
    if device_brand:
        query = query.filter(FactComplaintSample.device_brand.ilike(f"%{device_brand}%"))
    for column, value in (
        (FactComplaintSample.gender, gender),
        (FactComplaintSample.plan_id, plan_id),
        (FactComplaintSample.vip_level, vip_level),
        (FactComplaintSample.channel, channel),
        (FactComplaintSample.network_type, network_type),
    ):
        if value:
            query = query.filter(column == value)
    if age is not None:
        query = query.filter(FactComplaintSample.age == age)
    if monthly_fee is not None:
        query = query.filter(FactComplaintSample.monthly_fee == monthly_fee)
    if join_date is not None:
        query = query.filter(FactComplaintSample.join_date == join_date)
    if contract_end is not None:
        query = query.filter(FactComplaintSample.contract_end == contract_end)
    if fee_drift_rate is not None:
        query = query.filter(FactComplaintSample.fee_drift_rate == fee_drift_rate)
    if satisfaction_net is not None:
        query = query.filter(FactComplaintSample.satisfaction_net == satisfaction_net)
    if satisfaction_srv is not None:
        query = query.filter(FactComplaintSample.satisfaction_srv == satisfaction_srv)
    if satisfaction_score is not None:
        query = query.filter(FactComplaintSample.satisfaction_score == satisfaction_score)
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
        list=[InsightComplaintSampleRead.model_validate(_orm_columns_dict(row)) for row in rows],
        pageTotal=total,
    )


def list_touchpoints(
    db: Session,
    *,
    user_id: str | None = None,
    name: str | None = None,
    gender: str | None = None,
    msisdn: str | None = None,
    age: int | None = None,
    region: str | None = None,
    plan_id: str | None = None,
    vip_level: str | None = None,
    channel: str | None = None,
    device_brand: str | None = None,
    network_type: str | None = None,
    monthly_fee: float | None = None,
    join_date: date | None = None,
    contract_end: date | None = None,
    fee_drift_rate: float | None = None,
    satisfaction_net: int | None = None,
    satisfaction_srv: int | None = None,
    satisfaction_score: float | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 10,
) -> InsightTouchpointListResponse:
    return list_complaint_samples(
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


def list_category_pairs(db: Session) -> list[dict]:
    return crud_insight.list_category_pairs()


def _complaint_read(row: FactComplaintSample, region: str | None = None) -> InsightComplaintRead:
    data = InsightComplaintRead.model_validate(_orm_columns_dict(row)).model_dump()
    if not data.get("region") and region:
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
        .options(_DEFER_COMPLAINT_VECTOR)
        .outerjoin(DimUserProfile, FactComplaintSample.user_id == DimUserProfile.user_id)
        .filter(FactComplaintSample.complaint_id.isnot(None))
    )
    if user_id:
        query = query.filter(FactComplaintSample.user_id == user_id)
    if region:
        query = query.filter(
            or_(
                FactComplaintSample.region.ilike(f"%{region}%"),
                DimUserProfile.region.ilike(f"{region}%"),
            )
        )
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
    profile = db.get(DimUserProfile, data["user_id"])
    if profile is not None:
        for key in (
            "name",
            "age",
            "age_group",
            "region_l1",
            "region_l2",
            "region",
            "plan_id",
            "vip_level",
            "monthly_fee",
            "join_date",
            "fee_drift_rate",
            "gender",
            "msisdn",
            "channel",
            "device_brand",
            "network_type",
            "contract_end",
            "satisfaction_net",
            "satisfaction_srv",
        ):
            if data.get(key) is None:
                data[key] = getattr(profile, key)
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
    ):
        if value:
            query = query.filter(column.ilike(f"{value}%"))
    if churn_risk_level:
        query = query.filter(DimUserProfileSnapshot.churn_risk_level == churn_risk_level)
    snaps, total = _page(
        query.order_by(
            DimUserProfileSnapshot.snapshot_date.desc(),
            DimUserProfileSnapshot.risk_score.desc(),
        ),
        page,
        page_size,
    )
    page_ids = [row.user_id for row in snaps]
    profiles: dict[str, DimUserProfile] = {}
    if page_ids:
        profiles = {
            row.user_id: row
            for row in db.query(DimUserProfile).filter(DimUserProfile.user_id.in_(page_ids)).all()
        }
    items = []
    for snap in snaps:
        item = InsightProfileSnapshotRead.model_validate(snap)
        profile = profiles.get(snap.user_id)
        if profile is not None:
            item = item.model_copy(
                update={
                    "name": profile.name,
                    "gender": profile.gender,
                    "msisdn": profile.msisdn,
                    "age": profile.age,
                    "age_group": profile.age_group,
                    "region_l1": profile.region_l1,
                    "region_l2": profile.region_l2,
                    "region": profile.region,
                    "plan_id": profile.plan_id,
                    "vip_level": profile.vip_level,
                    "channel": profile.channel,
                    "device_brand": profile.device_brand,
                    "network_type": profile.network_type,
                    "join_date": profile.join_date,
                    "contract_end": profile.contract_end,
                    "monthly_fee": profile.monthly_fee,
                    "fee_drift_rate": profile.fee_drift_rate,
                    "satisfaction_net": profile.satisfaction_net,
                    "satisfaction_srv": profile.satisfaction_srv,
                    "sample_satisfaction": profile.sample_satisfaction,
                    "pred_satisfaction": profile.pred_satisfaction,
                }
            )
        items.append(item)
    return InsightProfileSnapshotListResponse(list=items, pageTotal=total)


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
            query = query.filter(column.ilike(f"{value}%"))
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
