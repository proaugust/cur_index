-- Insight 模块表结构 v2：客户主数据 + 样本事实 + 快照汇总

DROP TABLE IF EXISTS insight_risk_predictions CASCADE;
DROP TABLE IF EXISTS insight_complaints CASCADE;
DROP TABLE IF EXISTS insight_surveys CASCADE;
DROP TABLE IF EXISTS insight_customers CASCADE;
DROP TABLE IF EXISTS insight_complaint_categories CASCADE;
DROP TABLE IF EXISTS insight_region_risk_metrics CASCADE;
DROP TABLE IF EXISTS insight_user_profile_snapshot CASCADE;
DROP TABLE IF EXISTS insight_complaint_sample CASCADE;
DROP TABLE IF EXISTS insight_touchpoint_network_metric CASCADE;

CREATE TABLE IF NOT EXISTS insight_user_profile (
    user_id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    age INT NOT NULL,
    age_group VARCHAR(20) NOT NULL,
    region_l1 VARCHAR(30) NOT NULL,
    region_l2 VARCHAR(30) NOT NULL,
    region VARCHAR(50) NOT NULL,
    plan_id VARCHAR(20) NOT NULL,
    vip_level VARCHAR(20) NOT NULL DEFAULT '普通',
    join_date DATE NOT NULL,
    monthly_fee NUMERIC(10, 2) NOT NULL DEFAULT 0,
    fee_drift_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
    satisfaction_net INT CHECK (satisfaction_net IS NULL OR satisfaction_net BETWEEN 1 AND 5),
    satisfaction_srv INT CHECK (satisfaction_srv IS NULL OR satisfaction_srv BETWEEN 1 AND 5),
    risk_score NUMERIC(5, 4),
    risk_level VARCHAR(10),
    tags JSONB,
    shap_values JSONB
);

CREATE INDEX IF NOT EXISTS ix_insight_user_profile_age_group ON insight_user_profile (age_group);
CREATE INDEX IF NOT EXISTS ix_insight_user_profile_region ON insight_user_profile (region);
CREATE INDEX IF NOT EXISTS ix_insight_user_profile_region_l1 ON insight_user_profile (region_l1);
CREATE INDEX IF NOT EXISTS ix_insight_user_profile_region_l2 ON insight_user_profile (region_l2);
CREATE INDEX IF NOT EXISTS ix_insight_user_profile_plan_id ON insight_user_profile (plan_id);
CREATE INDEX IF NOT EXISTS ix_insight_user_profile_risk_score ON insight_user_profile (risk_score DESC);
CREATE INDEX IF NOT EXISTS ix_insight_user_profile_tags ON insight_user_profile USING GIN (tags);

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS insight_complaint_sample (
    sample_id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(32) NOT NULL,
    sample_time TIMESTAMP NOT NULL,
    record_date DATE NOT NULL,
    complaint_type VARCHAR(50),
    sub_category VARCHAR(50),
    satisfaction_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    survey_answers JSONB NOT NULL DEFAULT '[]',
    survey_category_scores JSONB NOT NULL DEFAULT '{}',
    complaint_id VARCHAR(32) UNIQUE,
    raw_text TEXT,
    complaint_vector vector(768)
);

CREATE INDEX IF NOT EXISTS ix_insight_sample_user_id ON insight_complaint_sample (user_id);
CREATE INDEX IF NOT EXISTS ix_insight_sample_record_date ON insight_complaint_sample (record_date DESC);
CREATE INDEX IF NOT EXISTS ix_insight_sample_complaint_id ON insight_complaint_sample (complaint_id);
CREATE INDEX IF NOT EXISTS ix_insight_sample_sample_time ON insight_complaint_sample (sample_time DESC);
CREATE INDEX IF NOT EXISTS ix_insight_sample_complaint_type ON insight_complaint_sample (complaint_type);
CREATE INDEX IF NOT EXISTS ix_insight_sample_sub_category ON insight_complaint_sample (sub_category);
CREATE INDEX IF NOT EXISTS ix_insight_sample_vector
ON insight_complaint_sample USING hnsw (complaint_vector vector_cosine_ops);

CREATE TABLE IF NOT EXISTS insight_user_profile_snapshot (
    snapshot_date DATE NOT NULL,
    user_id VARCHAR(32) NOT NULL,
    region_l1 VARCHAR(30) NOT NULL,
    region_l2 VARCHAR(30) NOT NULL,
    age_group VARCHAR(20) NOT NULL,
    plan_id VARCHAR(20) NOT NULL,
    vip_level VARCHAR(20) NOT NULL DEFAULT '普通',
    churn_risk_level VARCHAR(10) NOT NULL,
    activity_trend VARCHAR(20) NOT NULL DEFAULT 'stable',
    risk_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    tags JSONB,
    shap_values JSONB,
    PRIMARY KEY (snapshot_date, user_id)
);

CREATE INDEX IF NOT EXISTS ix_insight_snapshot_date ON insight_user_profile_snapshot (snapshot_date DESC);
CREATE INDEX IF NOT EXISTS ix_insight_snapshot_region ON insight_user_profile_snapshot (region_l1, region_l2);
CREATE INDEX IF NOT EXISTS ix_insight_snapshot_risk ON insight_user_profile_snapshot (churn_risk_level);

CREATE TABLE IF NOT EXISTS insight_region_risk_metrics (
    snapshot_date DATE NOT NULL,
    region_l1 VARCHAR(30) NOT NULL,
    region_l2 VARCHAR(30) NOT NULL,
    total_customers INT NOT NULL DEFAULT 0,
    high_risk_ratio NUMERIC(5, 4) NOT NULL DEFAULT 0,
    risk_ratio_mom NUMERIC(6, 4) NOT NULL DEFAULT 0,
    PRIMARY KEY (snapshot_date, region_l1, region_l2)
);

CREATE INDEX IF NOT EXISTS ix_insight_region_metrics_date ON insight_region_risk_metrics (snapshot_date DESC);

CREATE TABLE IF NOT EXISTS insight_simulation_weight (
    feature_name VARCHAR(50) PRIMARY KEY,
    base_importance NUMERIC(10, 4) NOT NULL,
    impact_coefficient NUMERIC(5, 2) NOT NULL
);

INSERT INTO insight_simulation_weight (feature_name, base_importance, impact_coefficient) VALUES
    ('satisfaction_srv', 1425.6500, -0.25),
    ('satisfaction_net', 1280.3200, -0.22),
    ('fee_drift_rate', 980.1500, 0.35),
    ('satisfaction_score', 875.4200, -0.18),
    ('monthly_fee', 520.3000, 0.08),
    ('vip_level', 410.1200, -0.12)
ON CONFLICT (feature_name) DO NOTHING;
