"""将 Insight 样本表改为问卷 JSON + 投诉信息结构。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    if "insight_touchpoint_network_metric" not in tables:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE insight_touchpoint_network_metric
                    ADD COLUMN IF NOT EXISTS survey_answers JSONB NOT NULL DEFAULT '[]'::jsonb,
                    ADD COLUMN IF NOT EXISTS survey_category_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
                    ADD COLUMN IF NOT EXISTS survey_total_score NUMERIC(5, 2) NOT NULL DEFAULT 0;
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE insight_touchpoint_network_metric
                    DROP COLUMN IF EXISTS avg_packet_loss,
                    DROP COLUMN IF EXISTS avg_rsrp,
                    DROP COLUMN IF EXISTS touchpoint_route,
                    DROP COLUMN IF EXISTS last_touchpoint;
                """
            )
        )
        conn.execute(
            text(
                """
                DELETE FROM insight_simulation_weight
                WHERE feature_name IN ('avg_packet_loss', 'avg_rsrp');

                INSERT INTO insight_simulation_weight (feature_name, base_importance, impact_coefficient)
                VALUES ('survey_total_score', 875.4200, -0.18)
                ON CONFLICT (feature_name) DO UPDATE
                SET base_importance = EXCLUDED.base_importance,
                    impact_coefficient = EXCLUDED.impact_coefficient;
                """
            )
        )
