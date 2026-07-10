"""统一 Insight 表名前缀：dim_/fact_/cfg_ → insight_（幂等）。"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

_RENAMES = (
    ("dim_user_profile", "insight_user_profile"),
    ("fact_complaint_log", "insight_complaint_log"),
    ("fact_touchpoint_network_metric", "insight_touchpoint_network_metric"),
    ("cfg_simulation_weight", "insight_simulation_weight"),
)


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def upgrade(engine: Engine) -> None:
    tables = _table_names(engine)
    with engine.begin() as conn:
        for old_name, new_name in _RENAMES:
            has_old = old_name in tables
            has_new = new_name in tables
            if has_old and not has_new:
                conn.execute(text(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"'))
                tables.discard(old_name)
                tables.add(new_name)
            elif has_old and has_new:
                conn.execute(text(f'DROP TABLE "{new_name}" CASCADE'))
                conn.execute(text(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"'))
                tables.discard(old_name)
                tables.add(new_name)
