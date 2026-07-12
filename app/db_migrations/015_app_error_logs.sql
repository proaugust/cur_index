-- 全局应用错误日志（admin 可查 / 直接 SQL 分析）
CREATE TABLE IF NOT EXISTS app_error_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(16) NOT NULL DEFAULT 'error',
    source VARCHAR(64) NOT NULL,
    error_type VARCHAR(128) NOT NULL DEFAULT '',
    message VARCHAR(500) NOT NULL DEFAULT '',
    detail TEXT,
    request_id VARCHAR(32),
    user_id INTEGER REFERENCES users(id),
    path VARCHAR(256),
    method VARCHAR(16),
    ref_type VARCHAR(64),
    ref_id VARCHAR(64),
    status VARCHAR(16) NOT NULL DEFAULT 'open'
);

CREATE INDEX IF NOT EXISTS ix_app_error_logs_created_at ON app_error_logs (created_at);
CREATE INDEX IF NOT EXISTS ix_app_error_logs_source_created ON app_error_logs (source, created_at);
CREATE INDEX IF NOT EXISTS ix_app_error_logs_error_type ON app_error_logs (error_type);
CREATE INDEX IF NOT EXISTS ix_app_error_logs_status ON app_error_logs (status);
