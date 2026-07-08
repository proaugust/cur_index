from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Permission, Role, User
from app.schemas_rbac import MenuCreate, MenuRead, MenuUpdate


def _permission_to_menu(permission: Permission, children_map: dict[str | None, list[Permission]]) -> MenuRead:
    children = [
        _permission_to_menu(child, children_map)
        for child in children_map.get(permission.code, [])
        if child.perm_type == "menu"
    ]
    return MenuRead(
        id=permission.code,
        pid=permission.parent_code,
        title=permission.name,
        index=permission.route_path or permission.code,
        icon=permission.icon,
        permiss=permission.code,
        is_system=permission.is_system,
        type="menu",
        children=children,
    )


def _build_menu_tree(rows: list[Permission]) -> list[MenuRead]:
    menu_rows = [row for row in rows if row.perm_type == "menu"]
    children_map: dict[str | None, list[Permission]] = {}
    for row in menu_rows:
        children_map.setdefault(row.parent_code, []).append(row)
    for items in children_map.values():
        items.sort(key=lambda item: item.code)
    roots = children_map.get(None, [])
    return [_permission_to_menu(row, children_map) for row in roots]


def list_menus(db: Session, actor: User) -> list[MenuRead]:
    if actor.role.level > 2:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看菜单")
    rows = db.query(Permission).order_by(Permission.code).all()
    return _build_menu_tree(rows)


def create_menu(db: Session, actor: User, payload: MenuCreate) -> MenuRead:
    if actor.role.level > 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可管理菜单")
    if db.query(Permission).filter(Permission.code == payload.code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="权限标识已存在")
    if payload.parent_code:
        parent = db.query(Permission).filter(Permission.code == payload.parent_code).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父菜单不存在")
    row = Permission(
        code=payload.code,
        name=payload.name,
        parent_code=payload.parent_code,
        perm_type="menu",
        route_path=payload.route_path,
        icon=payload.icon,
        is_system=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _permission_to_menu(row, {})


def update_menu(db: Session, actor: User, code: str, payload: MenuUpdate) -> MenuRead:
    if actor.role.level > 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可管理菜单")
    row = db.query(Permission).filter(Permission.code == code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="菜单不存在")
    if payload.name is not None:
        row.name = payload.name
    if payload.parent_code is not None:
        if payload.parent_code == code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父菜单不能是自己")
        if payload.parent_code:
            parent = db.query(Permission).filter(Permission.code == payload.parent_code).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="父菜单不存在")
        row.parent_code = payload.parent_code or None
    if payload.route_path is not None:
        row.route_path = payload.route_path
    if payload.icon is not None:
        row.icon = payload.icon
    db.commit()
    db.refresh(row)
    return _permission_to_menu(row, {})


def delete_menu(db: Session, actor: User, code: str) -> None:
    if actor.role.level > 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可管理菜单")
    row = db.query(Permission).filter(Permission.code == code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="菜单不存在")
    if row.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统内置菜单不可删除")
    if db.query(Permission).filter(Permission.parent_code == code).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请先删除子菜单")
    roles_using = db.query(Role).join(Role.permissions).filter(Permission.id == row.id).count()
    if roles_using > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="菜单仍被角色引用，无法删除")
    db.delete(row)
    db.commit()
