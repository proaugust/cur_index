-- 特征聚合：user_id IN (...) + record_date 过滤 / 30 天窗口
CREATE INDEX IF NOT EXISTS ix_insight_sample_user_record
    ON insight_complaint_sample (user_id, record_date);

CREATE INDEX IF NOT EXISTS ix_insight_sample_record_user_complaint
    ON insight_complaint_sample (record_date, user_id)
    WHERE complaint_id IS NOT NULL;
