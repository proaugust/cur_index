"""客户洞察（Insight）模块 ORM：客户主数据 + 样本事实 + 快照汇总。"""

from datetime import date, datetime
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.services.modules.insight.constants import COMPLAINT_VECTOR_DIM


class DimUserProfile(Base):
    """用户基础画像；风险字段仅作历史兼容，由快照表承载。"""

    __tablename__ = "insight_user_profile"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    age: Mapped[int] = mapped_column(Integer)
    age_group: Mapped[str] = mapped_column(String(20), index=True)
    region_l1: Mapped[str] = mapped_column(String(30), index=True)
    region_l2: Mapped[str] = mapped_column(String(30), index=True)
    region: Mapped[str] = mapped_column(String(50), index=True)
    plan_id: Mapped[str] = mapped_column(String(20), index=True)
    vip_level: Mapped[str] = mapped_column(String(20), default="普通")
    join_date: Mapped[date] = mapped_column(Date)
    monthly_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    fee_drift_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    satisfaction_net: Mapped[int | None] = mapped_column(Integer, nullable=True)
    satisfaction_srv: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True, index=True)
    risk_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    shap_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class FactComplaintSample(Base):
    """问卷 + 投诉原始样本事实表。"""

    __tablename__ = "insight_complaint_sample"

    sample_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    sample_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    record_date: Mapped[date] = mapped_column(Date, index=True)
    complaint_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    sub_category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    satisfaction_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    survey_answers: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    survey_category_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    complaint_id: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True, index=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    complaint_vector: Mapped[list[float] | None] = mapped_column(Vector(COMPLAINT_VECTOR_DIM), nullable=True)


class DimUserProfileSnapshot(Base):
    """用户风险标签日快照。"""

    __tablename__ = "insight_user_profile_snapshot"

    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    region_l1: Mapped[str] = mapped_column(String(30), index=True)
    region_l2: Mapped[str] = mapped_column(String(30), index=True)
    age_group: Mapped[str] = mapped_column(String(20))
    plan_id: Mapped[str] = mapped_column(String(20))
    vip_level: Mapped[str] = mapped_column(String(20))
    churn_risk_level: Mapped[str] = mapped_column(String(10), index=True)
    activity_trend: Mapped[str] = mapped_column(String(20), default="stable")
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    shap_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class FactRegionRiskMetrics(Base):
    """区域风险预聚合，供地图看板读取。"""

    __tablename__ = "insight_region_risk_metrics"

    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    region_l1: Mapped[str] = mapped_column(String(30), primary_key=True)
    region_l2: Mapped[str] = mapped_column(String(30), primary_key=True)
    total_customers: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_ratio: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=0)
    risk_ratio_mom: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=0)


class CfgSimulationWeight(Base):
    """WHAT-IF 仿真特征权重配置。"""

    __tablename__ = "insight_simulation_weight"

    feature_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    base_importance: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    impact_coefficient: Mapped[Decimal] = mapped_column(Numeric(5, 2))


class InsightAnalysisLog(Base):
    __tablename__ = "insight_analysis_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    tools_trace: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
