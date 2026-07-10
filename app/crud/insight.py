"""Insight 模块数据访问。"""

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.models.insight import (
    CfgSimulationWeight,
    DimUserProfile,
    DimUserProfileSnapshot,
    FactComplaintSample,
    FactRegionRiskMetrics,
    InsightAnalysisLog,
)
from app.services.modules.insight.constants import COMPLAINT_CATEGORY_TREE
from app.services.modules.insight.seed.profile_generator import strip_seed_meta


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
    sample_total = count_table(db, FactComplaintSample)
    complaint_total = int(
        db.scalar(
            select(func.count())
            .select_from(FactComplaintSample)
            .where(FactComplaintSample.complaint_id.isnot(None))
        )
        or 0
    )
    return {
        "users": count_table(db, DimUserProfile),
        "complaints": complaint_total,
        "touchpoints": sample_total,
        "samples": sample_total,
        "snapshots": count_table(db, DimUserProfileSnapshot),
        "region_metrics": count_table(db, FactRegionRiskMetrics),
        "simulation_weights": count_table(db, CfgSimulationWeight),
        "analysis_logs": count_table(db, InsightAnalysisLog),
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
    """清空用户主数据；调用前应确保样本与快照已清空。"""
    cleared = {"users": count_table(db, DimUserProfile)}
    db.execute(delete(DimUserProfile))
    db.commit()
    return cleared


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
