CREATE TABLE IF NOT EXISTS feature_intros (
    id SERIAL PRIMARY KEY,
    page_key VARCHAR(50) NOT NULL,
    section_key VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    CONSTRAINT uq_feature_intros_page_section UNIQUE (page_key, section_key)
);

CREATE INDEX IF NOT EXISTS ix_feature_intros_page_key ON feature_intros (page_key);
