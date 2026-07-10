"""合并 Insight 投诉日志到触点网络指标表，并将数组字段改为 JSONB。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def upgrade(engine: Engine) -> None:
    tables = _table_names(engine)
    if "insight_user_profile" not in tables or "insight_touchpoint_network_metric" not in tables:
        return

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(
            text(
                """
                ALTER TABLE insight_user_profile
                    ALTER COLUMN risk_score DROP DEFAULT,
                    ALTER COLUMN risk_score DROP NOT NULL,
                    ALTER COLUMN risk_level DROP DEFAULT,
                    ALTER COLUMN risk_level DROP NOT NULL,
                    ALTER COLUMN shap_values DROP DEFAULT,
                    ALTER COLUMN shap_values DROP NOT NULL;
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'insight_user_profile'
                          AND column_name = 'tags'
                          AND udt_name = '_text'
                    ) THEN
                        ALTER TABLE insight_user_profile
                            ALTER COLUMN tags DROP DEFAULT,
                            ALTER COLUMN tags DROP NOT NULL,
                            ALTER COLUMN tags TYPE JSONB USING to_jsonb(tags);
                    ELSE
                        ALTER TABLE insight_user_profile
                            ALTER COLUMN tags DROP DEFAULT,
                            ALTER COLUMN tags DROP NOT NULL;
                    END IF;
                END $$;
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE insight_touchpoint_network_metric
                    ADD COLUMN IF NOT EXISTS survey_answers JSONB NOT NULL DEFAULT '[]'::jsonb,
                    ADD COLUMN IF NOT EXISTS survey_category_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
                    ADD COLUMN IF NOT EXISTS survey_total_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
                    ADD COLUMN IF NOT EXISTS complaint_id VARCHAR(32),
                    ADD COLUMN IF NOT EXISTS complaint_time TIMESTAMP,
                    ADD COLUMN IF NOT EXISTS main_category VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS sub_category VARCHAR(50),
                    ADD COLUMN IF NOT EXISTS raw_text TEXT,
                    ADD COLUMN IF NOT EXISTS complaint_vector vector(768);
                """
            )
        )
        conn.execute(
            text(
                """
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'insight_touchpoint_network_metric'
                          AND column_name = 'touchpoint_route'
                          AND udt_name = '_text'
                    ) THEN
                        ALTER TABLE insight_touchpoint_network_metric
                            ALTER COLUMN touchpoint_route DROP DEFAULT,
                            ALTER COLUMN touchpoint_route TYPE JSONB USING to_jsonb(touchpoint_route),
                            ALTER COLUMN touchpoint_route SET DEFAULT '[]'::jsonb;
                    END IF;
                END $$;
                """
            )
        )

        if "insight_complaint_log" in tables:
            conn.execute(
                text(
                    """
                    INSERT INTO insight_touchpoint_network_metric (
                        user_id,
                        record_date,
                        survey_answers,
                        survey_category_scores,
                        survey_total_score,
                        complaint_id,
                        complaint_time,
                        main_category,
                        sub_category,
                        raw_text,
                        complaint_vector
                    )
                    SELECT
                        user_id,
                        complaint_time::date,
                        '[]'::jsonb,
                        '{}'::jsonb,
                        0,
                        complaint_id,
                        complaint_time,
                        main_category,
                        sub_category,
                        raw_text,
                        CASE
                            WHEN complaint_vector IS NOT NULL AND vector_dims(complaint_vector) = 768
                            THEN complaint_vector::vector(768)
                            ELSE NULL
                        END
                    FROM insight_complaint_log c
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM insight_touchpoint_network_metric t
                        WHERE t.complaint_id = c.complaint_id
                    );
                    """
                )
            )
            conn.execute(text("DROP TABLE IF EXISTS insight_complaint_log CASCADE"))

        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ix_insight_touchpoint_complaint_id
                    ON insight_touchpoint_network_metric (complaint_id)
                    WHERE complaint_id IS NOT NULL;
                CREATE INDEX IF NOT EXISTS ix_insight_touchpoint_complaint_time
                    ON insight_touchpoint_network_metric (complaint_time DESC);
                CREATE INDEX IF NOT EXISTS ix_insight_touchpoint_main_category
                    ON insight_touchpoint_network_metric (main_category);
                CREATE INDEX IF NOT EXISTS ix_insight_touchpoint_sub_category
                    ON insight_touchpoint_network_metric (sub_category);
                CREATE INDEX IF NOT EXISTS ix_insight_touchpoint_vector
                    ON insight_touchpoint_network_metric USING hnsw (complaint_vector vector_cosine_ops);
                CREATE INDEX IF NOT EXISTS ix_insight_user_profile_tags
                    ON insight_user_profile USING GIN (tags);
                """
            )
        )
