"""解除 Insight 样本表对客户画像表的外键依赖。"""

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
                DO $$
                DECLARE
                    constraint_name text;
                BEGIN
                    FOR constraint_name IN
                        SELECT tc.constraint_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage kcu
                          ON tc.constraint_name = kcu.constraint_name
                         AND tc.table_schema = kcu.table_schema
                        WHERE tc.table_name = 'insight_touchpoint_network_metric'
                          AND tc.constraint_type = 'FOREIGN KEY'
                          AND kcu.column_name = 'user_id'
                    LOOP
                        EXECUTE format(
                            'ALTER TABLE insight_touchpoint_network_metric DROP CONSTRAINT IF EXISTS %I',
                            constraint_name
                        );
                    END LOOP;
                END $$;
                """
            )
        )
