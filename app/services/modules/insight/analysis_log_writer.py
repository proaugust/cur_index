"""Insight 批处理分析日志：开始/收尾（独立 session 收尾）。"""

from __future__ import annotations

import logging
from datetime import date
from typing import Literal

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.insight import InsightAnalysisLog
from app.schemas.insight import InsightPipelineStepResult
from app.services.ops.error_log_service import record_app_error

logger = logging.getLogger(__name__)

_JOB_QUESTION = "insight-nightly-risk-pipeline"
InsightRunMode = Literal["incremental", "full"]


def begin_analysis_log(
    db: Session,
    *,
    snapshot_date: date,
    mode: InsightRunMode,
    pending_users: int,
) -> int:
    result = db.execute(
        update(InsightAnalysisLog)
        .where(
            InsightAnalysisLog.question == _JOB_QUESTION,
            InsightAnalysisLog.status == "running",
        )
        .values(status="failed", answer="中断：未正常收尾（超时/取消）")
        .execution_options(synchronize_session=None)
    )
    if result.rowcount:
        record_app_error(
            source="insight.nightly",
            message=f"收口 {result.rowcount} 条未完成批处理（超时/取消）",
            error_type="JobInterrupted",
            level="warning",
        )
    log = InsightAnalysisLog(
        question=_JOB_QUESTION,
        answer=f"开始 {snapshot_date} {mode} 管线，待评估 {pending_users} 人",
        status="running",
        tools_trace={
            "snapshot_date": snapshot_date.isoformat(),
            "mode": mode,
            "pending_users": pending_users,
        },
        latency_ms=0,
    )
    db.add(log)
    db.commit()
    return int(log.id)


def finish_analysis_log(
    *,
    log_id: int,
    status: str,
    snapshot_date: date,
    steps: list[InsightPipelineStepResult],
    snapshots: int,
    regions: int,
    elapsed_ms: int,
    prev_date: date | None,
    mode: InsightRunMode,
    model_version: str,
    error: str | None = None,
    exc: BaseException | None = None,
) -> None:
    db = SessionLocal()
    try:
        log = db.get(InsightAnalysisLog, log_id)
        if log is None:
            logger.warning("批处理日志不存在 id=%s，跳过收尾", log_id)
            return
        if status == "failed":
            log.answer = f"失败 {snapshot_date} {mode}：{error or 'unknown'}"
        else:
            log.answer = f"完成 {snapshot_date} {mode} 管线：快照 {snapshots} 条、区域 {regions} 条"
        log.status = status
        log.latency_ms = elapsed_ms
        log.tools_trace = {
            "snapshot_date": snapshot_date.isoformat(),
            "prev_snapshot_date": prev_date.isoformat() if prev_date else None,
            "model_version": model_version,
            "mode": mode,
            "snapshots_upserted": snapshots,
            "region_metrics_upserted": regions,
            "error": error,
            "steps": [step.model_dump() for step in steps],
        }
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    if status == "failed":
        record_app_error(
            source="insight.nightly",
            message=f"失败 {snapshot_date} {mode}：{error or 'unknown'}",
            error_type=exc.__class__.__name__ if exc else "NightlyFailed",
            exc=exc,
            detail=None if exc else error,
            ref_type="insight_analysis_log",
            ref_id=log_id,
        )
