"""将 Insight 投诉向量列统一为 768 维。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def upgrade(engine: Engine) -> None:
    tables = set(inspect(engine).get_table_names())
    if "insight_touchpoint_network_metric" not in tables:
        return

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text("DROP INDEX IF EXISTS ix_insight_touchpoint_vector"))
        conn.execute(
            text(
                """
                ALTER TABLE insight_touchpoint_network_metric
                    ADD COLUMN IF NOT EXISTS complaint_vector vector(768);
                """
            )
        )
        conn.execute(
            text(
                """
                UPDATE insight_touchpoint_network_metric
                SET complaint_vector = NULL
                WHERE complaint_vector IS NOT NULL
                  AND vector_dims(complaint_vector) <> 768;
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE insight_touchpoint_network_metric
                    ALTER COLUMN complaint_vector TYPE vector(768)
                    USING complaint_vector::vector(768);
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_insight_touchpoint_vector
                    ON insight_touchpoint_network_metric USING hnsw (complaint_vector vector_cosine_ops);
                """
            )
        )
