"""Insight 区域预聚合：从快照生成 insight_region_risk_metrics。"""

import logging
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, tuple_
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfileSnapshot, FactRegionRiskMetrics
from app.services.modules.insight.ai_risk_engine import RiskPrediction

logger = logging.getLogger(__name__)


class InsightRegionAggregator:
    def __init__(self, db: Session):
        self.db = db

    def aggregate(
        self,
        snapshot_date: date,
        predictions: list[RiskPrediction],
        *,
        replace_day: bool = True,
    ) -> int:
        prev_map = self._load_prev_ratios(snapshot_date)
        if replace_day:
            self.db.execute(delete(FactRegionRiskMetrics).where(FactRegionRiskMetrics.snapshot_date == snapshot_date))
            rows = self._build_rows(snapshot_date, predictions, prev_map)
        else:
            rows = self._rebuild_affected_regions(snapshot_date, predictions, prev_map)
        if rows:
            self.db.bulk_insert_mappings(FactRegionRiskMetrics, rows)
        self.db.commit()
        logger.info("区域聚合完成 date=%s regions=%s replace_day=%s", snapshot_date, len(rows), replace_day)
        return len(rows)

    def _rebuild_affected_regions(
        self,
        snapshot_date: date,
        predictions: list[RiskPrediction],
        prev_map: dict[tuple[str, str], Decimal],
    ) -> list[dict]:
        affected = {(item["region_l1"], item["region_l2"]) for item in predictions}
        if not affected:
            return []
        keys = list(affected)
        self.db.execute(
            delete(FactRegionRiskMetrics).where(
                FactRegionRiskMetrics.snapshot_date == snapshot_date,
                tuple_(FactRegionRiskMetrics.region_l1, FactRegionRiskMetrics.region_l2).in_(keys),
            )
        )
        snaps = (
            self.db.query(DimUserProfileSnapshot)
            .filter(
                DimUserProfileSnapshot.snapshot_date == snapshot_date,
                tuple_(DimUserProfileSnapshot.region_l1, DimUserProfileSnapshot.region_l2).in_(keys),
            )
            .all()
        )
        pseudo = [
            {
                "region_l1": row.region_l1,
                "region_l2": row.region_l2,
                "churn_risk_level": row.churn_risk_level,
            }
            for row in snaps
        ]
        return self._build_rows(snapshot_date, pseudo, prev_map)

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
        predictions: list[RiskPrediction] | list[dict],
        prev_map: dict[tuple[str, str], Decimal],
    ) -> list[dict]:
        buckets: dict[tuple[str, str], list] = defaultdict(list)
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
