-- document_chunks 向量检索索引：加速 RAG 相似度搜索

CREATE EXTENSION IF NOT EXISTS vector;

CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw
ON document_chunks USING hnsw (embedding vector_cosine_ops)
WHERE embedding IS NOT NULL;
