"""Insight 深夜批处理编排：AI → 快照落库 → 区域聚合。"""

import logging
import time
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, InsightAnalysisLog
from app.schemas.insight import InsightNightlyRunResult, InsightPipelineStepResult, InsightRiskBuildResult
from app.services.modules.insight.ai_risk_engine import InsightAiRiskEngine
from app.services.modules.insight.region_aggregator import InsightRegionAggregator
from app.services.modules.insight.snapshot_writer import InsightSnapshotWriter

logger = logging.getLogger(__name__)

_JOB_QUESTION = "insight-nightly-risk-pipeline"


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
        with_prev_day: bool = True,
    ) -> InsightNightlyRunResult:
        users = self.db.query(DimUserProfile).all()
        if not users:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无用户主数据，请先注入客户")

        target_date = snapshot_date or date.today()
        started = time.perf_counter()
        steps: list[InsightPipelineStepResult] = []
        prev_date: date | None = None
        prev_snapshots = 0
        prev_regions = 0

        if with_prev_day:
            prev_date = target_date - timedelta(days=1)
            prev_snapshots, prev_regions, prev_steps = self._run_pipeline(
                users, prev_date, dampen=Decimal("0.12")
            )
            steps.extend(prev_steps)

        snapshots, regions, today_steps = self._run_pipeline(users, target_date)
        steps.extend(today_steps)

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        log_id = self._write_analysis_log(
            snapshot_date=target_date,
            steps=steps,
            snapshots=snapshots,
            regions=regions,
            elapsed_ms=elapsed_ms,
            prev_date=prev_date,
        )
        self.db.commit()
        return InsightNightlyRunResult(
            snapshot_date=target_date,
            steps=steps,
            snapshots_upserted=snapshots,
            region_metrics_upserted=regions,
            analysis_log_id=log_id,
            elapsed_ms=elapsed_ms,
            model_version=self.ai_engine.model_version,
            prev_snapshot_date=prev_date,
            prev_snapshots_upserted=prev_snapshots,
            prev_region_metrics_upserted=prev_regions,
        )

    def build_snapshot(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
    ) -> InsightRiskBuildResult:
        result = self.run_nightly(snapshot_date=snapshot_date, with_prev_day=with_prev_day)
        return InsightRiskBuildResult(
            snapshot_date=result.snapshot_date,
            snapshots_upserted=result.snapshots_upserted,
            region_metrics_upserted=result.region_metrics_upserted,
            elapsed_ms=result.elapsed_ms,
            prev_snapshot_date=result.prev_snapshot_date,
            prev_snapshots_upserted=result.prev_snapshots_upserted,
            prev_region_metrics_upserted=result.prev_region_metrics_upserted,
        )

    def _run_pipeline(
        self,
        users: list[DimUserProfile],
        target_date: date,
        *,
        dampen: Decimal = Decimal("0"),
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

        snap_started = time.perf_counter()
        snapshots = self.snapshot_writer.write(target_date, predictions)
        steps.append(
            InsightPipelineStepResult(
                step="snapshot_writer",
                label="快照落库",
                output_count=snapshots,
                elapsed_ms=int((time.perf_counter() - snap_started) * 1000),
            )
        )

        agg_started = time.perf_counter()
        regions = self.region_aggregator.aggregate(target_date, predictions)
        steps.append(
            InsightPipelineStepResult(
                step="region_aggregator",
                label="区域聚合",
                output_count=regions,
                elapsed_ms=int((time.perf_counter() - agg_started) * 1000),
            )
        )
        return snapshots, regions, steps

    def _write_analysis_log(
        self,
        *,
        snapshot_date: date,
        steps: list[InsightPipelineStepResult],
        snapshots: int,
        regions: int,
        elapsed_ms: int,
        prev_date: date | None,
    ) -> int:
        trace = {
            "snapshot_date": snapshot_date.isoformat(),
            "prev_snapshot_date": prev_date.isoformat() if prev_date else None,
            "model_version": self.ai_engine.model_version,
            "snapshots_upserted": snapshots,
            "region_metrics_upserted": regions,
            "steps": [step.model_dump() for step in steps],
        }
        log = InsightAnalysisLog(
            question=_JOB_QUESTION,
            answer=f"完成 {snapshot_date} 深夜管线：快照 {snapshots} 条、区域 {regions} 条",
            status="completed",
            tools_trace=trace,
            latency_ms=elapsed_ms,
        )
        self.db.add(log)
        self.db.flush()
        return int(log.id)
