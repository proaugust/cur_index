"""Insight 区域预聚合：从快照生成 insight_region_risk_metrics。"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.insight import FactRegionRiskMetrics
from app.services.modules.insight.ai_risk_engine import RiskPrediction

logger = logging.getLogger(__name__)


class InsightRegionAggregator:
    def __init__(self, db: Session):
        self.db = db

    def aggregate(self, snapshot_date: date, predictions: list[RiskPrediction]) -> int:
        self.db.execute(delete(FactRegionRiskMetrics).where(FactRegionRiskMetrics.snapshot_date == snapshot_date))
        prev_map = self._load_prev_ratios(snapshot_date)
        rows = self._build_rows(snapshot_date, predictions, prev_map)
        if rows:
            self.db.bulk_insert_mappings(FactRegionRiskMetrics, rows)
        self.db.flush()
        logger.info("区域聚合完成 date=%s regions=%s", snapshot_date, len(rows))
        return len(rows)

    def _load_prev_ratios(self, snapshot_date: date) -> dict[tuple[str, str], Decimal]:
        prev_date = snapshot_date - timedelta(days=1)
        prev_rows = (
            self.db.query(FactRegionRiskMetrics)
            .filter(FactRegionRiskMetrics.snapshot_date == prev_date)
            .all()
        )
        return {(row.region_l1, row.region_l2): row.high_risk_ratio for row in prev_rows}

    def _build_rows(
        self,
        snapshot_date: date,
        predictions: list[RiskPrediction],
        prev_map: dict[tuple[str, str], Decimal],
    ) -> list[dict]:
        buckets: dict[tuple[str, str], list[RiskPrediction]] = defaultdict(list)
        for row in predictions:
            buckets[(row["region_l1"], row["region_l2"])].append(row)

        region_rows: list[dict] = []
        for (region_l1, region_l2), items in buckets.items():
            total = len(items)
            high_count = sum(1 for item in items if item["churn_risk_level"] == "high")
            high_ratio = Decimal(str(round(high_count / total, 4))) if total else Decimal("0")
            prev_ratio = prev_map.get((region_l1, region_l2))
            mom = (high_ratio - prev_ratio).quantize(Decimal("0.0001")) if prev_ratio is not None else Decimal("0")
            region_rows.append(
                {
                    "snapshot_date": snapshot_date,
                    "region_l1": region_l1,
                    "region_l2": region_l2,
                    "total_customers": total,
                    "high_risk_ratio": high_ratio,
                    "risk_ratio_mom": mom,
                }
            )
        return region_rows
