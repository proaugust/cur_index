-- 原始导入绝对路径（可空；历史数据保持 NULL）
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS original_import_path VARCHAR(1000);

ALTER TABLE document_business_chunks
    ADD COLUMN IF NOT EXISTS original_import_path VARCHAR(1000);
