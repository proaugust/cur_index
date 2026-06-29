import re

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import Permission, User
from app.services.permission_catalog import ROUTE_PERMISSION_MAP


def is_super_admin(user: User) -> bool:
    return user.role.level <= 1


def user_permission_codes(user: User) -> set[str]:
    return {p.code for p in user.role.permissions}


def user_menu_codes(user: User) -> set[str]:
    return {p.code for p in user.role.permissions if p.perm_type == "menu"}


def _normalize_path(path: str) -> str:
    path = path.rstrip("/") or "/"
    if not path.startswith("/"):
        path = "/" + path
    return path


def _match_path(template: str, actual: str) -> bool:
    template = _normalize_path(template)
    actual = _normalize_path(actual)
    pattern = "^" + re.sub(r"\{[^/]+\}", r"[^/]+", template) + "$"
    return re.match(pattern, actual) is not None


def resolve_api_permission(method: str, path: str, db: Session) -> str | None:
    method = method.upper()
    path = _normalize_path(path)
    exact = ROUTE_PERMISSION_MAP.get((method, path))
    if exact:
        return exact
    rows = db.query(Permission).filter(Permission.perm_type == "api", Permission.api_method == method).all()
    for row in rows:
        if row.api_path and _match_path(row.api_path, path):
            return row.code
    return None


def require_permission(code: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if is_super_admin(user):
            return user
        if code not in user_permission_codes(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限: {code}")
        return user

    return checker


def require_api(method: str, path: str):
    def checker(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        if is_super_admin(user):
            return user
        code = resolve_api_permission(method, path, db)
        if not code:
            return user
        if code not in user_permission_codes(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少接口权限: {code}")
        return user

    return checker
