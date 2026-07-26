"""真实流失标签：CSV 导入与派生（观察日后 90 天内离网）。"""

import csv
import io
from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, FactComplaintSample, FactChurnLabel
from app.services.modules.insight.constants import (
    CHURN_HORIZON_DAYS,
    LABEL_SOURCE_CSV,
    LABEL_SOURCE_SEED,
)
from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
from app.services.modules.insight.seed.churn_label_generator import (
    default_as_of_dates,
    sample_churn_label,
)


class InsightChurnLabelService:
    def __init__(self, db: Session):
        self.db = db

    def count(self) -> int:
        return int(self.db.query(FactChurnLabel).count())

    def clear(self) -> int:
        total = self.count()
        self.db.query(FactChurnLabel).delete()
        self.db.flush()
        return total

    def seed_synthetic(self) -> int:
        """按样本特征概率采样 churn_90d，供无 CRM 时验证算法（非 weak_label）。"""
        sample_ids = {uid for (uid,) in self.db.query(FactComplaintSample.user_id).distinct()}
        if not sample_ids:
            return 0
        users = self.db.query(DimUserProfile).filter(DimUserProfile.user_id.in_(sample_ids)).all()
        if not users:
            return 0
        self.db.query(FactChurnLabel).filter(FactChurnLabel.label_source == LABEL_SOURCE_SEED).delete()
        occupied = {
            (uid, as_of)
            for uid, as_of in self.db.query(FactChurnLabel.user_id, FactChurnLabel.as_of_date).all()
        }
        builder = InsightFeatureBuilder(self.db)
        mappings: list[dict] = []
        for as_of in default_as_of_dates():
            features = builder.build_batch(users, as_of_date=as_of)
            for user in users:
                if user.join_date > as_of or (user.user_id, as_of) in occupied:
                    continue
                feature = features.get(user.user_id)
                if not feature or not feature.has_sample:
                    continue
                churn, cancel = sample_churn_label(user, feature, as_of)
                mappings.append(
                    {
                        "user_id": user.user_id,
                        "as_of_date": as_of,
                        "churn_90d": churn,
                        "label_source": LABEL_SOURCE_SEED,
                        "cancel_date": cancel,
                    }
                )
        if mappings:
            self.db.bulk_insert_mappings(FactChurnLabel, mappings)
        self.db.commit()
        return len(mappings)

    def import_csv(self, raw: bytes, *, as_of_date: date | None = None) -> dict:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV 无表头")
        fields = {name.strip().lower() for name in reader.fieldnames if name}
        rows = list(reader)
        if "churn_90d" in fields and "as_of_date" in fields:
            upserted, skipped = self._import_explicit(rows)
        elif "cancel_date" in fields:
            if as_of_date is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="仅含 cancel_date 时须指定 as_of_date 查询参数",
                )
            upserted, skipped = self._import_from_cancel(rows, as_of_date)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV 需含 user_id,as_of_date,churn_90d 或 user_id,cancel_date",
            )
        self.db.flush()
        return {"upserted": upserted, "skipped": skipped, "total": self.count()}

    def _import_explicit(self, rows: list[dict]) -> tuple[int, int]:
        upserted = skipped = 0
        for row in rows:
            user_id = _cell(row, "user_id")
            as_of = _parse_date(_cell(row, "as_of_date"))
            churn = _parse_int(_cell(row, "churn_90d"))
            if not user_id or as_of is None or churn is None:
                skipped += 1
                continue
            cancel = _parse_date(_cell(row, "cancel_date"))
            source = _cell(row, "label_source") or LABEL_SOURCE_CSV
            self._upsert(user_id, as_of, int(churn), source, cancel)
            upserted += 1
        return upserted, skipped

    def _import_from_cancel(self, rows: list[dict], as_of: date) -> tuple[int, int]:
        upserted = skipped = 0
        horizon_end = as_of + timedelta(days=CHURN_HORIZON_DAYS)
        for row in rows:
            user_id = _cell(row, "user_id")
            if not user_id:
                skipped += 1
                continue
            cancel = _parse_date(_cell(row, "cancel_date"))
            label = _derive_churn(cancel, as_of, horizon_end)
            if label is None:
                skipped += 1
                continue
            self._upsert(user_id, as_of, label, LABEL_SOURCE_CSV, cancel)
            upserted += 1
        return upserted, skipped

    def _upsert(
        self,
        user_id: str,
        as_of: date,
        churn: int,
        source: str,
        cancel: date | None,
    ) -> None:
        existing = self.db.get(FactChurnLabel, (user_id, as_of))
        if existing:
            existing.churn_90d = churn
            existing.label_source = source
            existing.cancel_date = cancel
            return
        self.db.add(
            FactChurnLabel(
                user_id=user_id,
                as_of_date=as_of,
                churn_90d=churn,
                label_source=source,
                cancel_date=cancel,
            )
        )


def _derive_churn(cancel: date | None, as_of: date, horizon_end: date) -> int | None:
    if cancel is not None and cancel <= as_of:
        return None
    if cancel is None or cancel > horizon_end:
        return 0
    return 1


def _cell(row: dict, key: str) -> str:
    for name, value in row.items():
        if name and name.strip().lower() == key:
            return str(value or "").strip()
    return ""


def _parse_date(raw: str) -> date | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_int(raw: str) -> int | None:
    if raw == "":
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None
