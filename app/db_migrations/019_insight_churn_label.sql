-- 真实流失标签表：观察日 as_of 后 90 天内是否销户/携转
CREATE TABLE IF NOT EXISTS insight_churn_label (
    user_id VARCHAR(32) NOT NULL,
    as_of_date DATE NOT NULL,
    churn_90d INTEGER NOT NULL DEFAULT 0,
    label_source VARCHAR(32) NOT NULL DEFAULT 'csv_import',
    cancel_date DATE NULL,
    PRIMARY KEY (user_id, as_of_date)
);

CREATE INDEX IF NOT EXISTS ix_insight_churn_label_churn
    ON insight_churn_label (churn_90d);

CREATE INDEX IF NOT EXISTS ix_insight_churn_label_as_of
    ON insight_churn_label (as_of_date);
