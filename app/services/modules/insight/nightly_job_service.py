"""Insight 深夜批处理编排：AI → 快照落库 → 区域聚合（支持增量/全量）。"""

import logging
import time
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, DimUserProfileSnapshot
from app.schemas.insight import (
    InsightNightlyJobAccepted,
    InsightNightlyRunResult,
    InsightPipelineStepResult,
    InsightRiskBuildResult,
)
from app.services.modules.insight.analysis_log_writer import begin_analysis_log, finish_analysis_log
from app.services.modules.insight.ai_risk_engine import InsightAiRiskEngine
from app.services.modules.insight.region_aggregator import InsightRegionAggregator
from app.services.modules.insight.snapshot_writer import InsightSnapshotWriter

logger = logging.getLogger(__name__)

InsightRunMode = Literal["incremental", "full"]


class InsightNightlyJobService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_engine = InsightAiRiskEngine()
        self.snapshot_writer = InsightSnapshotWriter(db)
        self.region_aggregator = InsightRegionAggregator(db)

    def prepare_async(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
        mode: InsightRunMode = "incremental",
    ) -> InsightNightlyJobAccepted:
        del with_prev_day
        target_date = snapshot_date or date.today()
        users = self._load_users(target_date, mode=mode)
        if not users and mode == "full":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无用户主数据，请先注入客户")
        log_id = begin_analysis_log(self.db, snapshot_date=target_date, mode=mode, pending_users=len(users))
        return InsightNightlyJobAccepted(
            analysis_log_id=log_id,
            snapshot_date=target_date,
            mode=mode,
            pending_users=len(users),
        )

    def run_nightly(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
        mode: InsightRunMode = "incremental",
        existing_log_id: int | None = None,
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
        snapshots, regions = 0, 0
        elapsed_ms = 0
        replace_day = mode == "full"
        log_id = existing_log_id or begin_analysis_log(
            self.db, snapshot_date=target_date, mode=mode, pending_users=len(users)
        )
        outcome_status = "failed"
        outcome_error: str | None = None
        outcome_exc: BaseException | None = None

        try:
            if with_prev_day:
                prev_date = target_date - timedelta(days=1)
                prev_users = users if mode == "full" else self._load_users(prev_date, mode=mode)
                if prev_users:
                    prev_snapshots, prev_regions, prev_steps = self._run_pipeline(
                        prev_users, prev_date, dampen=Decimal("0.12"), replace_day=replace_day
                    )
                    steps.extend(prev_steps)

            if users:
                snapshots, regions, today_steps = self._run_pipeline(users, target_date, replace_day=replace_day)
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
            outcome_status = "completed"
        except BaseException as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            outcome_error = str(exc)[:500] or exc.__class__.__name__
            outcome_exc = exc
            try:
                self.db.rollback()
            except Exception:
                logger.exception("批处理失败后 rollback 异常")
            raise
        finally:
            try:
                finish_analysis_log(
                    log_id=log_id,
                    status=outcome_status,
                    snapshot_date=target_date,
                    steps=steps,
                    snapshots=snapshots if outcome_status == "completed" else 0,
                    regions=regions if outcome_status == "completed" else 0,
                    elapsed_ms=elapsed_ms,
                    prev_date=prev_date,
                    mode=mode,
                    model_version=self.ai_engine.model_version,
                    error=outcome_error,
                    exc=outcome_exc,
                )
            except Exception:
                logger.exception("批处理日志收尾失败 id=%s status=%s", log_id, outcome_status)

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
