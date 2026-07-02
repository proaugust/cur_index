-- complaints 表查询索引（阶段一）：批量任务部分索引 + 明细/统计组合索引

CREATE INDEX IF NOT EXISTS ix_complaints_unclassified
ON complaints (id)
WHERE category_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_complaints_no_embedding
ON complaints (id)
WHERE embedding IS NULL;

CREATE INDEX IF NOT EXISTS ix_complaints_time_id_desc
ON complaints (complaint_time DESC, id DESC);

CREATE INDEX IF NOT EXISTS ix_complaints_cat_time_id
ON complaints (category_id, complaint_time DESC, id DESC);
