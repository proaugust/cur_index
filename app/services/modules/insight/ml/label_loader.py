"""训练标签收集：优先真实流失标签，否则弱标签 fallback。"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, FactChurnLabel
from app.services.modules.insight.constants import LABEL_SOURCE_REAL, LABEL_SOURCE_WEAK
from app.services.modules.insight.ml.feature_builder import InsightFeatureBuilder
from app.services.modules.insight.ml.types import UserFeatureRow
from app.services.modules.insight.ml.weak_label import weak_label


@dataclass
class LabeledTrainRow:
    user_id: str
    label: int
    as_of_date: date | None
    values: list[float]


def collect_train_rows(db: Session, users: list[DimUserProfile]) -> tuple[list[LabeledTrainRow], str]:
    """有 insight_churn_label 则用真实标签+as_of 特征；否则弱标签。"""
    real_rows = _collect_real(db, users)
    if real_rows:
        return real_rows, LABEL_SOURCE_REAL
    return _collect_weak(db, users), LABEL_SOURCE_WEAK


def _collect_real(db: Session, users: list[DimUserProfile]) -> list[LabeledTrainRow]:
    labels = db.query(FactChurnLabel).all()
    if not labels:
        return []
    user_map = {u.user_id: u for u in users}
    builder = InsightFeatureBuilder(db)
    by_date: dict[date, list[FactChurnLabel]] = {}
    for row in labels:
        if row.user_id not in user_map:
            continue
        by_date.setdefault(row.as_of_date, []).append(row)

    out: list[LabeledTrainRow] = []
    for as_of, group in by_date.items():
        batch_users = [user_map[r.user_id] for r in group if user_map[r.user_id].join_date <= as_of]
        if not batch_users:
            continue
        features = builder.build_batch(batch_users, as_of_date=as_of)
        out.extend(_rows_from_labels(group, features, as_of))
    return out


def _rows_from_labels(
    group: list[FactChurnLabel],
    features: dict[str, UserFeatureRow],
    as_of: date,
) -> list[LabeledTrainRow]:
    rows: list[LabeledTrainRow] = []
    for row in group:
        feature = features.get(row.user_id)
        if not feature or not feature.has_sample:
            continue
        rows.append(
            LabeledTrainRow(
                user_id=row.user_id,
                label=int(row.churn_90d),
                as_of_date=as_of,
                values=list(feature.values),
            )
        )
    return rows


def _collect_weak(db: Session, users: list[DimUserProfile]) -> list[LabeledTrainRow]:
    features = InsightFeatureBuilder(db).build_batch(users)
    rows: list[LabeledTrainRow] = []
    for user in users:
        feature = features.get(user.user_id)
        if not feature or not feature.has_sample:
            continue
        rows.append(
            LabeledTrainRow(
                user_id=user.user_id,
                label=weak_label(user, feature),
                as_of_date=None,
                values=list(feature.values),
            )
        )
    return rows
