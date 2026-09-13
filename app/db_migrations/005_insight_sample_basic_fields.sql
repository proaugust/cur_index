-- 样本表补齐与客户主数据对齐的基础字段
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS join_date DATE;
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS fee_drift_rate NUMERIC(5, 2);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS satisfaction_net INTEGER;
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS satisfaction_srv INTEGER;
