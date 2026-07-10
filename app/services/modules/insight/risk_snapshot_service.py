"""Insight 风险快照门面（兼容旧接口，内部委托深夜批处理编排）。"""

from datetime import date

from sqlalchemy.orm import Session

from app.schemas.insight import InsightNightlyRunResult, InsightRiskBuildResult
from app.services.modules.insight.nightly_job_service import InsightNightlyJobService


class InsightRiskSnapshotService:
    def __init__(self, db: Session):
        self._job = InsightNightlyJobService(db)

    def run_nightly(self, snapshot_date: date | None = None, *, with_prev_day: bool = False) -> InsightNightlyRunResult:
        return self._job.run_nightly(snapshot_date=snapshot_date, with_prev_day=with_prev_day)

    def build_snapshot(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
    ) -> InsightRiskBuildResult:
        return self._job.build_snapshot(snapshot_date=snapshot_date, with_prev_day=with_prev_day)
