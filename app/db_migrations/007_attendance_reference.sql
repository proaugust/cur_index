-- 考勤人员标准照字段（老库补列；新库由 create_all 已含）
ALTER TABLE attendance_persons
    ADD COLUMN IF NOT EXISTS reference_image VARCHAR(500);

ALTER TABLE attendance_persons
    ADD COLUMN IF NOT EXISTS reference_score DOUBLE PRECISION;
