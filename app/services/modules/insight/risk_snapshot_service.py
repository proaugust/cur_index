"""Insight 风险快照门面：后台启动深夜批处理。"""

from datetime import date
from typing import Literal

from app.schemas.insight import InsightNightlyJobAccepted
from app.services.modules.insight.nightly_job_runner import start_nightly_async

InsightRunMode = Literal["incremental", "full"]


class InsightRiskSnapshotService:
    def run_nightly(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
        mode: InsightRunMode = "incremental",
    ) -> InsightNightlyJobAccepted:
        return start_nightly_async(snapshot_date=snapshot_date, with_prev_day=with_prev_day, mode=mode)

    def build_snapshot(
        self,
        snapshot_date: date | None = None,
        *,
        with_prev_day: bool = False,
        mode: InsightRunMode = "incremental",
    ) -> InsightNightlyJobAccepted:
        return start_nightly_async(snapshot_date=snapshot_date, with_prev_day=with_prev_day, mode=mode)
