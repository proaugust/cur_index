"""Insight 模块数据访问。"""

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.models.insight import (
    CfgSimulationWeight,
    DimUserProfile,
    DimUserProfileSnapshot,
    FactChurnLabel,
    FactComplaintSample,
    FactRegionRiskMetrics,
    InsightAnalysisLog,
)
from app.services.modules.insight.constants import COMPLAINT_CATEGORY_TREE
from app.services.modules.insight.seed.profile_generator import strip_seed_meta

# 样本 → 客户：人属性 + 真值满意度（1 样本 = 1 客户）
_SAMPLE_PROFILE_ALIGN_FIELDS = (
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
)
_PROFILE_FROM_SAMPLE_EXTRA = ("satisfaction_net", "satisfaction_srv", "sample_satisfaction")


def count_table(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


_USER_ID_BASE = 10_000_000


def sync_user_seq(db: Session) -> None:
    """按库内最大 user_id 续号，支持多次追加注入。"""
    from app.services.modules.insight.seed.profile_generator import reset_user_seq

    max_user_id = db.scalar(select(func.max(DimUserProfile.user_id)))
    if max_user_id and str(max_user_id).isdigit():
        reset_user_seq(int(max_user_id) - _USER_ID_BASE)
    else:
        reset_user_seq(0)


def sync_complaint_seq(db: Session) -> None:
    """按库内最大 complaint_id 尾号续号，支持多次追加注入。"""
    from app.services.modules.insight.seed.complaint_generator import reset_complaint_seq

    max_cid = db.scalar(
        select(func.max(FactComplaintSample.complaint_id)).where(FactComplaintSample.complaint_id.isnot(None))
    )
    if max_cid and len(str(max_cid)) >= 14 and str(max_cid)[-5:].isdigit():
        reset_complaint_seq(int(str(max_cid)[-5:]))
    else:
        reset_complaint_seq(0)


def get_seed_status(db: Session) -> dict[str, int]:
    # 单次 round-trip：多标量子查询，避免多次往返
    row = db.execute(
        select(
            select(func.count()).select_from(DimUserProfile).scalar_subquery().label("users"),
            select(func.count())
            .select_from(FactComplaintSample)
            .where(FactComplaintSample.complaint_id.isnot(None))
            .scalar_subquery()
            .label("complaints"),
            select(func.count()).select_from(FactComplaintSample).scalar_subquery().label("samples"),
            select(func.count()).select_from(DimUserProfileSnapshot).scalar_subquery().label("snapshots"),
            select(func.count()).select_from(FactRegionRiskMetrics).scalar_subquery().label("region_metrics"),
            select(func.count()).select_from(CfgSimulationWeight).scalar_subquery().label("simulation_weights"),
            select(func.count()).select_from(InsightAnalysisLog).scalar_subquery().label("analysis_logs"),
            select(func.count()).select_from(FactChurnLabel).scalar_subquery().label("churn_labels"),
        )
    ).one()
    sample_total = int(row.samples or 0)
    return {
        "users": int(row.users or 0),
        "complaints": int(row.complaints or 0),
        "touchpoints": sample_total,
        "samples": sample_total,
        "snapshots": int(row.snapshots or 0),
        "region_metrics": int(row.region_metrics or 0),
        "simulation_weights": int(row.simulation_weights or 0),
        "analysis_logs": int(row.analysis_logs or 0),
        "churn_labels": int(row.churn_labels or 0),
    }


def clear_sample_data(db: Session) -> dict[str, int]:
    """清空样本事实表，保留用户主数据。"""
    sample_total = count_table(db, FactComplaintSample)
    complaint_total = int(
        db.scalar(
            select(func.count())
            .select_from(FactComplaintSample)
            .where(FactComplaintSample.complaint_id.isnot(None))
        )
        or 0
    )
    cleared = {
        "complaints": complaint_total,
        "touchpoints": sample_total,
        "samples": sample_total,
    }
    db.execute(delete(FactComplaintSample))
    db.commit()
    return cleared


def clear_churn_labels(db: Session) -> dict[str, int]:
    cleared = {"churn_labels": count_table(db, FactChurnLabel)}
    db.execute(delete(FactChurnLabel))
    db.commit()
    return cleared


def clear_snapshot_data(db: Session) -> dict[str, int]:
    cleared = {
        "snapshots": count_table(db, DimUserProfileSnapshot),
        "region_metrics": count_table(db, FactRegionRiskMetrics),
    }
    db.execute(delete(DimUserProfileSnapshot))
    db.execute(delete(FactRegionRiskMetrics))
    db.commit()
    return cleared


def clear_user_data(db: Session) -> dict[str, int]:
    """清空用户主数据；与样本/快照互不影响。"""
    cleared = {"users": count_table(db, DimUserProfile)}
    db.execute(delete(DimUserProfile))
    db.commit()
    return cleared


def _profile_payload_from_dict(row: dict) -> dict:
    """只保留客户主表可写字段。"""
    clean = strip_seed_meta(row)
    allowed = {"user_id", *_SAMPLE_PROFILE_ALIGN_FIELDS, *_PROFILE_FROM_SAMPLE_EXTRA}
    return {k: v for k, v in clean.items() if k in allowed and v is not None}


def bulk_upsert_profiles_from_samples(db: Session, rows: list[dict]) -> int:
    """按 user_id 仅插入尚不存在的客户（已并入则跳过，不覆盖）。"""
    if not rows:
        return 0
    inserted = 0
    for row in rows:
        payload = _profile_payload_from_dict(row)
        user_id = payload.get("user_id")
        if not user_id:
            continue
        existing = db.get(DimUserProfile, user_id)
        if existing is not None:
            continue
        db.add(DimUserProfile(**payload))
        inserted += 1
    db.commit()
    return inserted


def promote_samples_to_customers(db: Session) -> dict[str, int]:
    """将尚未并入的样本升成客户：保留样本自身 user_id；已存在的客户跳过。

    新造数 1 样本 = 1 user_id；若历史数据多人共用同一 user_id，则满意度取均值。
    """
    samples = db.query(FactComplaintSample).order_by(FactComplaintSample.sample_id).all()
    if not samples:
        return {"promoted": 0, "profiles_upserted": 0, "skipped": 0}

    by_user: dict[str, list[FactComplaintSample]] = defaultdict(list)
    for sample in samples:
        by_user[sample.user_id].append(sample)

    rows: list[dict] = []
    for uid, group in by_user.items():
        s0 = group[0]
        if s0.name is None or s0.age is None or s0.join_date is None:
            continue
        sats = [float(s.satisfaction_score) for s in group]
        nets = [s.satisfaction_net for s in group if s.satisfaction_net is not None]
        srvs = [s.satisfaction_srv for s in group if s.satisfaction_srv is not None]
        row: dict = {"user_id": uid, "sample_satisfaction": Decimal(str(round(sum(sats) / len(sats), 2)))}
        for field in _SAMPLE_PROFILE_ALIGN_FIELDS:
            row[field] = getattr(s0, field)
        if nets:
            row["satisfaction_net"] = int(round(sum(nets) / len(nets)))
        if srvs:
            row["satisfaction_srv"] = int(round(sum(srvs) / len(srvs)))
        rows.append(row)

    inserted = bulk_upsert_profiles_from_samples(db, rows)
    skipped = len(rows) - inserted
    return {"promoted": inserted, "profiles_upserted": inserted, "skipped": skipped}


def bulk_insert_profiles(db: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    db.bulk_insert_mappings(DimUserProfile, [strip_seed_meta(row) for row in rows])
    db.commit()
    return len(rows)


def bulk_insert_complaint_samples(db: Session, rows: list[dict]) -> int:
    if not rows:
        return 0
    db.bulk_insert_mappings(FactComplaintSample, rows)
    db.commit()
    return len(rows)


def bulk_insert_complaint_touchpoints(db: Session, rows: list[dict]) -> int:
    return bulk_insert_complaint_samples(db, rows)


def list_category_pairs() -> list[dict]:
    pairs: list[dict] = []
    for main_category, subs in COMPLAINT_CATEGORY_TREE.items():
        for sub_category in subs:
            pairs.append({"main_category": main_category, "sub_category": sub_category})
    return pairs


def random_user_rows(db: Session, limit: int) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT user_id, name, age, age_group, region_l1, region_l2, region, plan_id, vip_level,
                   join_date, monthly_fee, fee_drift_rate, satisfaction_net, satisfaction_srv,
                   risk_score, risk_level, tags, shap_values
            FROM insight_user_profile
            ORDER BY random()
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    result = []
    for row in rows:
        item = dict(row)
        item["_province"] = item.get("region_l1") or (str(item.get("region", "")).split("·")[0])
        item["_city"] = item.get("region_l2") or (str(item.get("region", "")).split("·")[-1])
        result.append(item)
    return result
