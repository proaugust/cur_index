-- 样本表对齐客户人属性；客户表增加预测满意度（连续值评估用）
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS name VARCHAR(50);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS age INTEGER;
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS age_group VARCHAR(20);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS region_l1 VARCHAR(30);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS region_l2 VARCHAR(30);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS region VARCHAR(50);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS plan_id VARCHAR(20);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS vip_level VARCHAR(20);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS monthly_fee NUMERIC(10, 2);

ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS pred_satisfaction NUMERIC(5, 2);
ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS sample_satisfaction NUMERIC(5, 2);
