"""从主数据 + 样本事实构建模型特征矩阵。"""

from collections import defaultdict
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.insight import DimUserProfile, FactComplaintSample
from app.services.modules.insight.ml.feature_labels import (
    COMPLAINT_TYPE_KEYS,
    FEATURE_NAMES,
    SURVEY_KEYS,
    VIP_ORDINAL,
)
from app.services.modules.insight.ml.types import UserFeatureRow

# 分批 IN，避免待评估用户过多时退化为三次全表扫描
FEATURE_AGG_CHUNK = 2000


class InsightFeatureBuilder:
    def __init__(self, db: Session):
        self.db = db

    def build_batch(self, users: list[DimUserProfile]) -> dict[str, UserFeatureRow]:
        user_map = {user.user_id: user for user in users}
        agg = self._load_aggregates(list(user_map.keys()))
        rows: dict[str, UserFeatureRow] = {}
        today = date.today()
        for user_id, user in user_map.items():
            stat = agg.get(
                user_id,
                {
                    "sample_cnt": 0,
                    "complaint_cnt": 0,
                    "avg_satisfaction": None,
                    "dominant_type": None,
                    "ctype_counts": {},
                    "survey_scores": {},
                },
            )
            rows[user_id] = UserFeatureRow(
                user_id=user_id,
                has_sample=stat["sample_cnt"] > 0,
                complaint_cnt=int(stat["complaint_cnt"]),
                avg_satisfaction=stat["avg_satisfaction"],
                dominant_type=stat["dominant_type"],
                values=self._build_vector(user, stat, today),
            )
        return rows

    def _build_vector(self, user: DimUserProfile, stat: dict, today: date) -> list[float]:
        tenure = max(0.0, (today - user.join_date).days / 365.25)
        ctype_counts = stat["ctype_counts"]
        survey_scores = stat["survey_scores"]
        avg_sat = stat["avg_satisfaction"] if stat["avg_satisfaction"] is not None else 3.0
        values: list[float] = [
            float(user.age),
            float(user.monthly_fee or 0),
            float(user.fee_drift_rate or 0),
            float(user.satisfaction_net or 3),
            float(user.satisfaction_srv or 3),
            float(VIP_ORDINAL.get(user.vip_level, 0)),
            round(tenure, 2),
            float(stat["sample_cnt"]),
            float(stat["complaint_cnt"]),
            float(avg_sat),
        ]
        values.extend(float(ctype_counts.get(name, 0)) for name in COMPLAINT_TYPE_KEYS)
        values.extend(float(survey_scores.get(key, 3.0)) for key in SURVEY_KEYS)
        return values

    def _load_base_counts(self, use_in_clause: bool, user_ids: list[str] | None) -> dict[str, dict]:
        base_q = self.db.query(
            FactComplaintSample.user_id,
            func.count(FactComplaintSample.sample_id),
            func.count(FactComplaintSample.complaint_id),
            func.avg(FactComplaintSample.satisfaction_score),
        )
        if use_in_clause and user_ids:
            base_q = base_q.filter(FactComplaintSample.user_id.in_(user_ids))
        base_rows = base_q.group_by(FactComplaintSample.user_id).all()

        agg: dict[str, dict] = {}
        for user_id, sample_cnt, complaint_cnt, avg_score in base_rows:
            agg[user_id] = {
                "sample_cnt": int(sample_cnt),
                "complaint_cnt": int(complaint_cnt or 0),
                "avg_satisfaction": float(avg_score) if avg_score is not None else None,
                "dominant_type": None,
                "ctype_counts": defaultdict(int),
                "survey_scores": defaultdict(list),
            }
        return agg

    def _load_complaint_types(self, agg: dict[str, dict], use_in_clause: bool, user_ids: list[str] | None) -> None:
        type_q = (
            self.db.query(
                FactComplaintSample.user_id,
                FactComplaintSample.complaint_type,
                func.count(FactComplaintSample.sample_id),
            )
            .filter(FactComplaintSample.complaint_type.isnot(None))
        )
        if use_in_clause and user_ids:
            type_q = type_q.filter(FactComplaintSample.user_id.in_(user_ids))
        for user_id, complaint_type, count in type_q.group_by(
            FactComplaintSample.user_id, FactComplaintSample.complaint_type
        ).all():
            bucket = agg.setdefault(
                user_id,
                {
                    "sample_cnt": 0,
                    "complaint_cnt": 0,
                    "avg_satisfaction": None,
                    "dominant_type": None,
                    "ctype_counts": defaultdict(int),
                    "survey_scores": defaultdict(list),
                },
            )
            bucket["ctype_counts"][complaint_type] += int(count)

    def _load_survey_scores(self, agg: dict[str, dict], use_in_clause: bool, user_ids: list[str] | None) -> None:
        survey_q = self.db.query(
            FactComplaintSample.user_id,
            FactComplaintSample.survey_category_scores,
        ).filter(FactComplaintSample.survey_category_scores.isnot(None))
        if use_in_clause and user_ids:
            survey_q = survey_q.filter(FactComplaintSample.user_id.in_(user_ids))
        for user_id, scores in survey_q.all():
            if not scores:
                continue
            bucket = agg.setdefault(
                user_id,
                {
                    "sample_cnt": 0,
                    "complaint_cnt": 0,
                    "avg_satisfaction": None,
                    "dominant_type": None,
                    "ctype_counts": defaultdict(int),
                    "survey_scores": defaultdict(list),
                },
            )
            for key, value in scores.items():
                bucket["survey_scores"][key].append(float(value))

    def _load_aggregates(self, user_ids: list[str] | None = None) -> dict[str, dict]:
        if user_ids is not None and not user_ids:
            return {}
        if user_ids is None:
            agg = self._load_base_counts(False, None)
            self._load_complaint_types(agg, False, None)
            self._load_survey_scores(agg, False, None)
            return self._finalize_aggregates(agg)

        agg: dict[str, dict] = {}
        for offset in range(0, len(user_ids), FEATURE_AGG_CHUNK):
            chunk = user_ids[offset : offset + FEATURE_AGG_CHUNK]
            part = self._load_base_counts(True, chunk)
            self._load_complaint_types(part, True, chunk)
            self._load_survey_scores(part, True, chunk)
            agg.update(part)
        return self._finalize_aggregates(agg)

    @staticmethod
    def _finalize_aggregates(agg: dict[str, dict]) -> dict[str, dict]:
        for bucket in agg.values():
            if bucket["ctype_counts"]:
                bucket["dominant_type"] = max(bucket["ctype_counts"], key=bucket["ctype_counts"].get)
            bucket["survey_scores"] = {
                key: round(sum(values) / len(values), 2)
                for key, values in bucket["survey_scores"].items()
                if values
            }
            bucket["ctype_counts"] = dict(bucket["ctype_counts"])
        return agg

    @staticmethod
    def feature_names() -> list[str]:
        return list(FEATURE_NAMES)
