"""三层架构：样本表改名 + 用户快照 + 区域风险汇总。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _rename_column(conn, table: str, old: str, new: str) -> None:
    cols = {c["name"] for c in inspect(conn).get_columns(table)}
    if old in cols and new not in cols:
        conn.execute(text(f'ALTER TABLE {table} RENAME COLUMN "{old}" TO "{new}"'))


def upgrade(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())

    if "insight_touchpoint_network_metric" in tables and "insight_complaint_sample" not in tables:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE insight_touchpoint_network_metric RENAME TO insight_complaint_sample"))
        tables.discard("insight_touchpoint_network_metric")
        tables.add("insight_complaint_sample")

    if "insight_complaint_sample" in tables:
        with engine.begin() as conn:
            _rename_column(conn, "insight_complaint_sample", "log_id", "sample_id")
            _rename_column(conn, "insight_complaint_sample", "complaint_time", "sample_time")
            _rename_column(conn, "insight_complaint_sample", "main_category", "complaint_type")
            _rename_column(conn, "insight_complaint_sample", "survey_total_score", "satisfaction_score")
            conn.execute(
                text(
                    """
                    UPDATE insight_complaint_sample
                    SET sample_time = COALESCE(sample_time, record_date::timestamp),
                        record_date = COALESCE(record_date, sample_time::date)
                    WHERE sample_time IS NULL OR record_date IS NULL;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE insight_complaint_sample
                        ALTER COLUMN sample_time SET NOT NULL,
                        ALTER COLUMN record_date SET NOT NULL;
                    """
                )
            )

    if "insight_user_profile" in tables:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    ALTER TABLE insight_user_profile
                        ADD COLUMN IF NOT EXISTS region_l1 VARCHAR(30),
                        ADD COLUMN IF NOT EXISTS region_l2 VARCHAR(30);
                    """
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE insight_user_profile
                    SET region_l1 = COALESCE(region_l1, split_part(region, '·', 1)),
                        region_l2 = COALESCE(region_l2, NULLIF(split_part(region, '·', 2), ''))
                    WHERE region IS NOT NULL;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    UPDATE insight_user_profile
                    SET region_l2 = region_l1
                    WHERE region_l2 IS NULL OR region_l2 = '';
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE insight_user_profile
                        ALTER COLUMN region_l1 SET NOT NULL,
                        ALTER COLUMN region_l2 SET NOT NULL;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    ALTER TABLE insight_user_profile
                        ALTER COLUMN satisfaction_net DROP NOT NULL,
                        ALTER COLUMN satisfaction_srv DROP NOT NULL;
                    """
                )
            )
            conn.execute(
                text(
                    """
                    CREATE INDEX IF NOT EXISTS ix_insight_user_profile_region_l1
                        ON insight_user_profile (region_l1);
                    CREATE INDEX IF NOT EXISTS ix_insight_user_profile_region_l2
                        ON insight_user_profile (region_l2);
                    """
                )
            )

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS insight_user_profile_snapshot (
                    snapshot_date DATE NOT NULL,
                    user_id VARCHAR(32) NOT NULL,
                    region_l1 VARCHAR(30) NOT NULL,
                    region_l2 VARCHAR(30) NOT NULL,
                    age_group VARCHAR(20) NOT NULL,
                    plan_id VARCHAR(20) NOT NULL,
                    vip_level VARCHAR(20) NOT NULL DEFAULT '普通',
                    churn_risk_level VARCHAR(10) NOT NULL,
                    activity_trend VARCHAR(20) NOT NULL DEFAULT 'stable',
                    risk_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
                    tags JSONB,
                    shap_values JSONB,
                    PRIMARY KEY (snapshot_date, user_id)
                );
                CREATE INDEX IF NOT EXISTS ix_insight_snapshot_date
                    ON insight_user_profile_snapshot (snapshot_date DESC);
                CREATE INDEX IF NOT EXISTS ix_insight_snapshot_region
                    ON insight_user_profile_snapshot (region_l1, region_l2);
                CREATE INDEX IF NOT EXISTS ix_insight_snapshot_risk
                    ON insight_user_profile_snapshot (churn_risk_level);

                CREATE TABLE IF NOT EXISTS insight_region_risk_metrics (
                    snapshot_date DATE NOT NULL,
                    region_l1 VARCHAR(30) NOT NULL,
                    region_l2 VARCHAR(30) NOT NULL,
                    total_customers INT NOT NULL DEFAULT 0,
                    high_risk_ratio NUMERIC(5, 4) NOT NULL DEFAULT 0,
                    risk_ratio_mom NUMERIC(6, 4) NOT NULL DEFAULT 0,
                    PRIMARY KEY (snapshot_date, region_l1, region_l2)
                );
                CREATE INDEX IF NOT EXISTS ix_insight_region_metrics_date
                    ON insight_region_risk_metrics (snapshot_date DESC);
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE insight_simulation_weight
                SET feature_name = 'satisfaction_score'
                WHERE feature_name = 'survey_total_score';

                INSERT INTO insight_simulation_weight (feature_name, base_importance, impact_coefficient)
                VALUES ('satisfaction_score', 875.4200, -0.18)
                ON CONFLICT (feature_name) DO NOTHING;
                """
            )
        )
