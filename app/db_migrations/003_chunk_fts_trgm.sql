-- 切块表 FTS / 路径模糊检索索引（部署环境只跑一次）
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS lang VARCHAR(8) NOT NULL DEFAULT 'zh';
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS search_vector tsvector;
ALTER TABLE document_chunks
    ADD COLUMN IF NOT EXISTS original_import_path VARCHAR(1000);

ALTER TABLE document_business_chunks
    ADD COLUMN IF NOT EXISTS lang VARCHAR(8) NOT NULL DEFAULT 'zh';
ALTER TABLE document_business_chunks
    ADD COLUMN IF NOT EXISTS search_vector tsvector;
ALTER TABLE document_business_chunks
    ADD COLUMN IF NOT EXISTS original_import_path VARCHAR(1000);
ALTER TABLE document_business_chunks
    ADD COLUMN IF NOT EXISTS corpus_name VARCHAR(200) NOT NULL DEFAULT '';

CREATE INDEX IF NOT EXISTS ix_dcc_business_corpus
ON document_business_chunks (corpus_name);

CREATE INDEX IF NOT EXISTS ix_dcc_business_src
ON document_business_chunks (source_file);

CREATE INDEX IF NOT EXISTS ix_document_chunks_fts
ON document_chunks USING gin (search_vector);

CREATE INDEX IF NOT EXISTS ix_dcc_business_fts
ON document_business_chunks USING gin (search_vector);

CREATE INDEX IF NOT EXISTS ix_document_chunks_source_file_trgm
ON document_chunks USING gin (source_file gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_dcc_business_src_trgm
ON document_business_chunks USING gin (source_file gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_dcc_business_hnsw
ON document_business_chunks USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;
