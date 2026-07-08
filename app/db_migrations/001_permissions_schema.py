"""permissions 表结构补丁（幂等，可安全重复逻辑）。"""

from sqlalchemy.engine import Engine

from app.services.system.rbac_seed import ensure_permission_schema


def upgrade(engine: Engine) -> None:
    ensure_permission_schema(engine)
