-- 客户/样本对齐：性别、号码、渠道、终端、网络制式、合约到期
ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS msisdn VARCHAR(20);
ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS channel VARCHAR(30);
ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS device_brand VARCHAR(50);
ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS network_type VARCHAR(10);
ALTER TABLE insight_user_profile ADD COLUMN IF NOT EXISTS contract_end DATE;

ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS gender VARCHAR(10);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS msisdn VARCHAR(20);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS channel VARCHAR(30);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS device_brand VARCHAR(50);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS network_type VARCHAR(10);
ALTER TABLE insight_complaint_sample ADD COLUMN IF NOT EXISTS contract_end DATE;
