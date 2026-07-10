-- 客户洞察（Insight）模块：6 张核心表 + 分类种子数据

-- ① 客户画像（目标 500 万）
CREATE TABLE IF NOT EXISTS insight_customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    gender VARCHAR(10) NOT NULL DEFAULT '未知',
    age SMALLINT NOT NULL,
    city VARCHAR(50) NOT NULL,
    province VARCHAR(50) NOT NULL,
    package_type VARCHAR(50) NOT NULL,
    monthly_fee NUMERIC(10, 2) NOT NULL DEFAULT 0,
    vip_level VARCHAR(20) NOT NULL DEFAULT '普通',
    register_date DATE NOT NULL,
    network_type VARCHAR(10) NOT NULL DEFAULT '5G',
    device VARCHAR(80) NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_insight_customers_province_city
ON insight_customers (province, city);

CREATE INDEX IF NOT EXISTS ix_insight_customers_package_type
ON insight_customers (package_type);

CREATE INDEX IF NOT EXISTS ix_insight_customers_register_date
ON insight_customers (register_date);

-- ④ 投诉分类（一级 + 二级）
CREATE TABLE IF NOT EXISTS insight_complaint_categories (
    id SERIAL PRIMARY KEY,
    parent_id INTEGER REFERENCES insight_complaint_categories (id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    level SMALLINT NOT NULL CHECK (level IN (1, 2)),
    sort_order SMALLINT NOT NULL DEFAULT 0,
    CONSTRAINT uq_insight_complaint_cat_parent_name UNIQUE (parent_id, name)
);

CREATE INDEX IF NOT EXISTS ix_insight_complaint_categories_parent
ON insight_complaint_categories (parent_id);

-- ③ 投诉记录（正文 80~150 字自然描述）
CREATE TABLE IF NOT EXISTS insight_complaints (
    complaint_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES insight_customers (customer_id) ON DELETE CASCADE,
    complaint_time TIMESTAMP NOT NULL,
    type_id INTEGER NOT NULL REFERENCES insight_complaint_categories (id),
    sub_type_id INTEGER NOT NULL REFERENCES insight_complaint_categories (id),
    complaint_type VARCHAR(50) NOT NULL,
    sub_type VARCHAR(50) NOT NULL,
    complaint_text TEXT NOT NULL,
    sentiment VARCHAR(20) NOT NULL DEFAULT '负面',
    status VARCHAR(20) NOT NULL DEFAULT '处理中',
    satisfaction_after SMALLINT CHECK (satisfaction_after IS NULL OR satisfaction_after BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS ix_insight_complaints_customer_id
ON insight_complaints (customer_id);

CREATE INDEX IF NOT EXISTS ix_insight_complaints_complaint_time
ON insight_complaints (complaint_time DESC);

CREATE INDEX IF NOT EXISTS ix_insight_complaints_type_sub
ON insight_complaints (complaint_type, sub_type);

CREATE INDEX IF NOT EXISTS ix_insight_complaints_status
ON insight_complaints (status);

CREATE INDEX IF NOT EXISTS ix_insight_complaints_time_type
ON insight_complaints (complaint_time DESC, type_id, sub_type_id);

-- ② 满意度调查（目标 5 万，各项 1~5 分）
CREATE TABLE IF NOT EXISTS insight_surveys (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES insight_customers (customer_id) ON DELETE CASCADE,
    survey_date DATE NOT NULL,
    network_score SMALLINT NOT NULL CHECK (network_score BETWEEN 1 AND 5),
    customer_service_score SMALLINT NOT NULL CHECK (customer_service_score BETWEEN 1 AND 5),
    billing_score SMALLINT NOT NULL CHECK (billing_score BETWEEN 1 AND 5),
    signal_score SMALLINT NOT NULL CHECK (signal_score BETWEEN 1 AND 5),
    price_score SMALLINT NOT NULL CHECK (price_score BETWEEN 1 AND 5),
    app_score SMALLINT NOT NULL CHECK (app_score BETWEEN 1 AND 5),
    recommend_score SMALLINT NOT NULL CHECK (recommend_score BETWEEN 1 AND 5),
    overall_score SMALLINT NOT NULL CHECK (overall_score BETWEEN 1 AND 5)
);

CREATE INDEX IF NOT EXISTS ix_insight_surveys_customer_id
ON insight_surveys (customer_id);

CREATE INDEX IF NOT EXISTS ix_insight_surveys_survey_date
ON insight_surveys (survey_date DESC);

-- ⑤ 风险预测结果（LightGBM）
CREATE TABLE IF NOT EXISTS insight_risk_predictions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES insight_customers (customer_id) ON DELETE CASCADE,
    risk_score NUMERIC(6, 4) NOT NULL,
    complaint_probability NUMERIC(6, 4) NOT NULL,
    main_reason VARCHAR(200) NOT NULL DEFAULT '',
    model_version VARCHAR(32) NOT NULL,
    predict_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_insight_risk_predictions_customer
ON insight_risk_predictions (customer_id, predict_time DESC);

CREATE INDEX IF NOT EXISTS ix_insight_risk_predictions_score
ON insight_risk_predictions (risk_score DESC);

CREATE UNIQUE INDEX IF NOT EXISTS uq_insight_risk_customer_model
ON insight_risk_predictions (customer_id, model_version);

-- ⑥ AI 分析日志
CREATE TABLE IF NOT EXISTS insight_analysis_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    tools_trace JSONB,
    user_id INTEGER REFERENCES users (id) ON DELETE SET NULL,
    latency_ms INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_insight_analysis_logs_created_at
ON insight_analysis_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_insight_analysis_logs_user_id
ON insight_analysis_logs (user_id);
