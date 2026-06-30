from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Permission, Role, User
from app.services.permission_catalog import (
    ADMIN_MENU_PERMISSIONS,
    API_PERMISSIONS,
    MENU_PERMISSIONS,
    SUPER_ADMIN_MENU_PERMISSIONS,
    USER_MENU_PERMISSIONS,
    default_permissions_for_menus,
)


def ensure_permission_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if "permissions" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("permissions")}
    alters: list[str] = []
    if "route_path" not in columns:
        alters.append("ADD COLUMN route_path VARCHAR(200)")
    if "icon" not in columns:
        alters.append("ADD COLUMN icon VARCHAR(50)")
    if "is_system" not in columns:
        alters.append("ADD COLUMN is_system BOOLEAN DEFAULT TRUE")
    if "perm_type" not in columns:
        alters.append("ADD COLUMN perm_type VARCHAR(10) DEFAULT 'menu'")
    if "api_method" not in columns:
        alters.append("ADD COLUMN api_method VARCHAR(10)")
    if "api_path" not in columns:
        alters.append("ADD COLUMN api_path VARCHAR(200)")
    if alters:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE permissions " + ", ".join(alters)))
    # 扩大 code 字段
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE permissions ALTER COLUMN code TYPE VARCHAR(80)"))


def _ensure_permissions(db: Session) -> dict[str, Permission]:
    code_map: dict[str, Permission] = {}
    for code, name, parent_code, route_path, icon in MENU_PERMISSIONS:
        row = db.query(Permission).filter(Permission.code == code).first()
        if not row:
            row = Permission(
                code=code,
                name=name,
                parent_code=parent_code,
                perm_type="menu",
                route_path=route_path,
                icon=icon,
                is_system=True,
            )
            db.add(row)
        else:
            row.name = name
            row.parent_code = parent_code
            row.perm_type = "menu"
            row.route_path = route_path
            row.icon = icon
            row.is_system = True
        code_map[code] = row

    for menu_code, api_id, name, method, path in API_PERMISSIONS:
        code = f"{menu_code}.{api_id}"
        row = code_map.get(code)
        if row is None:
            row = db.query(Permission).filter(Permission.code == code).first()
        if not row:
            row = Permission(
                code=code,
                name=name,
                parent_code=menu_code,
                perm_type="api",
                api_method=method,
                api_path=path,
                is_system=True,
            )
            db.add(row)
        else:
            row.name = name
            row.parent_code = menu_code
            row.perm_type = "api"
            row.api_method = method
            row.api_path = path
            row.is_system = True
        code_map[code] = row

    db.commit()
    for row in code_map.values():
        db.refresh(row)
    return code_map


def _set_role_permissions(db: Session, role: Role, codes: list[str], code_map: dict[str, Permission]) -> None:
    role.permissions = [code_map[code] for code in codes if code in code_map]
    db.commit()
    db.refresh(role)


def seed_rbac(db: Session) -> None:
    code_map = _ensure_permissions(db)

    roles_spec = [
        ("超级管理员", "super_admin", 1, True, default_permissions_for_menus(SUPER_ADMIN_MENU_PERMISSIONS, include_admin_only_apis=True)),
        ("管理员", "admin", 2, True, default_permissions_for_menus(ADMIN_MENU_PERMISSIONS, include_admin_only_apis=True)),
        ("用户", "user", 3, True, default_permissions_for_menus(USER_MENU_PERMISSIONS)),
    ]
    role_by_key: dict[str, Role] = {}
    for name, key, level, is_system, permiss in roles_spec:
        role = db.query(Role).filter(Role.key == key).first()
        if not role:
            role = Role(name=name, key=key, level=level, is_system=is_system, status=True)
            db.add(role)
            db.commit()
            db.refresh(role)
        else:
            role.name = name
            role.level = level
            role.is_system = is_system
            db.commit()
        _set_role_permissions(db, role, permiss, code_map)
        role_by_key[key] = role

    admin_password = "admin123456"
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            password_hash=hash_password(admin_password),
            email="admin@local",
            phone="",
            role_id=role_by_key["super_admin"].id,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
    else:
        admin_user.password_hash = hash_password(admin_password)
        db.commit()
