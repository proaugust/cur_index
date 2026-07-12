"""Insight 深夜批处理编排：AI → 快照落库 → 区域聚合（支持增量/全量）。"""

import logging
import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, DimUserProfileSnapshot, InsightAnalysisLog
from app.schemas.insight import InsightNightlyRunResult, InsightPipelineStepResult, InsightRiskBuildResult
from app.services.modules.insight.ai_risk_engine import InsightAiRiskEngine
from app.services.modules.insight.region_aggregator import InsightRegionAggregator
from app.services.modules.insight.snapshot_writer import InsightSnapshotWriter

logger = logging.getLogger(__name__)

_JOB_QUESTION = "insight-nightly-risk-pipeline"
InsightRunMode = Literal["incremental", "full"]


class InsightNightlyJobService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_engine = InsightAiRiskEngine()
        self.snapshot_writer = InsightSnapshotWriter(db)
        self.region_aggregator = InsightRegionAggregator(db)

    def run_nightly(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
        mode: InsightRunMode = "incremental",
    ) -> InsightNightlyRunResult:
        target_date = snapshot_date or date.today()
        users = self._load_users(target_date, mode=mode)
        if not users and mode == "full":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无用户主数据，请先注入客户")

        started = time.perf_counter()
        steps: list[InsightPipelineStepResult] = []
        prev_date: date | None = None
        prev_snapshots = 0
        prev_regions = 0
        replace_day = mode == "full"
        # 先落 running 日志并 commit，避免 HF 超时导致「完全无日志」
        log_id = self._begin_analysis_log(snapshot_date=target_date, mode=mode, pending_users=len(users))

        try:
            if with_prev_day:
                prev_date = target_date - timedelta(days=1)
                prev_users = users if mode == "full" else self._load_users(prev_date, mode=mode)
                if prev_users:
                    prev_snapshots, prev_regions, prev_steps = self._run_pipeline(
                        prev_users, prev_date, dampen=Decimal("0.12"), replace_day=replace_day
                    )
                    steps.extend(prev_steps)

            snapshots, regions = 0, 0
            if users:
                snapshots, regions, today_steps = self._run_pipeline(
                    users, target_date, replace_day=replace_day
                )
                steps.extend(today_steps)
            else:
                steps.append(
                    InsightPipelineStepResult(
                        step="ai_risk_engine",
                        label="AI 风险计算（无待评估客户）",
                        output_count=0,
                        elapsed_ms=0,
                    )
                )

            elapsed_ms = int((time.perf_counter() - started) * 1000)
            self._finish_analysis_log(
                log_id,
                status="completed",
                snapshot_date=target_date,
                steps=steps,
                snapshots=snapshots,
                regions=regions,
                elapsed_ms=elapsed_ms,
                prev_date=prev_date,
                mode=mode,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            try:
                self.db.rollback()
            except Exception:
                logger.exception("批处理失败后 rollback 异常")
            self._finish_analysis_log(
                log_id,
                status="failed",
                snapshot_date=target_date,
                steps=steps,
                snapshots=0,
                regions=0,
                elapsed_ms=elapsed_ms,
                prev_date=prev_date,
                mode=mode,
                error=str(exc)[:500],
            )
            raise

        return InsightNightlyRunResult(
            snapshot_date=target_date,
            steps=steps,
            snapshots_upserted=snapshots,
            region_metrics_upserted=regions,
            analysis_log_id=log_id,
            elapsed_ms=elapsed_ms,
            model_version=self.ai_engine.model_version,
            mode=mode,
            prev_snapshot_date=prev_date,
            prev_snapshots_upserted=prev_snapshots,
            prev_region_metrics_upserted=prev_regions,
        )

    def build_snapshot(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
        mode: InsightRunMode = "incremental",
    ) -> InsightRiskBuildResult:
        result = self.run_nightly(snapshot_date=snapshot_date, with_prev_day=with_prev_day, mode=mode)
        return InsightRiskBuildResult(
            snapshot_date=result.snapshot_date,
            snapshots_upserted=result.snapshots_upserted,
            region_metrics_upserted=result.region_metrics_upserted,
            elapsed_ms=result.elapsed_ms,
            mode=result.mode,
            prev_snapshot_date=result.prev_snapshot_date,
            prev_snapshots_upserted=result.prev_snapshots_upserted,
            prev_region_metrics_upserted=result.prev_region_metrics_upserted,
        )

    def _load_users(self, snapshot_date: date, *, mode: InsightRunMode) -> list[DimUserProfile]:
        if mode == "full":
            return self.db.query(DimUserProfile).all()
        scored_today = (
            self.db.query(DimUserProfileSnapshot.user_id)
            .filter(DimUserProfileSnapshot.snapshot_date == snapshot_date)
            .subquery()
        )
        return (
            self.db.query(DimUserProfile)
            .outerjoin(scored_today, DimUserProfile.user_id == scored_today.c.user_id)
            .filter(or_(DimUserProfile.risk_score.is_(None), scored_today.c.user_id.is_(None)))
            .all()
        )

    def _run_pipeline(
        self,
        users: list[DimUserProfile],
        target_date: date,
        *,
        dampen: Decimal = Decimal("0"),
        replace_day: bool = True,
    ) -> tuple[int, int, list[InsightPipelineStepResult]]:
        steps: list[InsightPipelineStepResult] = []
        ai_started = time.perf_counter()
        predictions = self.ai_engine.run(self.db, users, dampen=dampen)
        steps.append(
            InsightPipelineStepResult(
                step="ai_risk_engine",
                label="AI 风险计算",
                output_count=len(predictions),
                elapsed_ms=int((time.perf_counter() - ai_started) * 1000),
            )
        )
        self.db.expunge_all()

        snap_started = time.perf_counter()
        snapshots = self.snapshot_writer.write(target_date, predictions, replace_day=replace_day)
        steps.append(
            InsightPipelineStepResult(
                step="snapshot_writer",
                label="快照落库",
                output_count=snapshots,
                elapsed_ms=int((time.perf_counter() - snap_started) * 1000),
            )
        )

        agg_started = time.perf_counter()
        regions = self.region_aggregator.aggregate(target_date, predictions, replace_day=replace_day)
        steps.append(
            InsightPipelineStepResult(
                step="region_aggregator",
                label="区域聚合",
                output_count=regions,
                elapsed_ms=int((time.perf_counter() - agg_started) * 1000),
            )
        )
        return snapshots, regions, steps

    def _begin_analysis_log(self, *, snapshot_date: date, mode: InsightRunMode, pending_users: int) -> int:
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
        self.db.add(log)
        self.db.commit()
        return int(log.id)

    def _finish_analysis_log(
        self,
        log_id: int,
        *,
        status: str,
        snapshot_date: date,
        steps: list[InsightPipelineStepResult],
        snapshots: int,
        regions: int,
        elapsed_ms: int,
        prev_date: date | None,
        mode: InsightRunMode,
        error: str | None = None,
    ) -> None:
        log = self.db.get(InsightAnalysisLog, log_id)
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
            "model_version": self.ai_engine.model_version,
            "mode": mode,
            "snapshots_upserted": snapshots,
            "region_metrics_upserted": regions,
            "error": error,
            "steps": [step.model_dump() for step in steps],
        }
        self.db.commit()
