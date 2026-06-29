from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Permission, User
from app.schemas_rbac import PermissionTreeNode, PermissionTreeResponse


def build_permission_tree(rows: list[Permission]) -> list[PermissionTreeNode]:
    menus = [row for row in rows if row.perm_type == "menu"]
    apis_by_parent: dict[str, list[Permission]] = {}
    for row in rows:
        if row.perm_type == "api" and row.parent_code:
            apis_by_parent.setdefault(row.parent_code, []).append(row)
    for items in apis_by_parent.values():
        items.sort(key=lambda item: item.code)

    children_map: dict[str | None, list[Permission]] = {}
    for row in menus:
        children_map.setdefault(row.parent_code, []).append(row)
    for items in children_map.values():
        items.sort(key=lambda item: item.code)

    def build_level(parent_code: str | None) -> list[PermissionTreeNode]:
        result: list[PermissionTreeNode] = []
        for row in children_map.get(parent_code, []):
            child_nodes = build_level(row.code)
            api_children = [
                PermissionTreeNode(
                    id=api.code,
                    title=api.name,
                    type="api",
                    api_method=api.api_method,
                    api_path=api.api_path,
                    children=[],
                )
                for api in apis_by_parent.get(row.code, [])
            ]
            result.append(
                PermissionTreeNode(
                    id=row.code,
                    title=row.name,
                    type="menu",
                    children=child_nodes + api_children,
                )
            )
        return result

    return build_level(None)


def list_permission_tree(db: Session, actor: User) -> PermissionTreeResponse:
    if actor.role.level > 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可编辑角色权限")
    rows = db.query(Permission).order_by(Permission.code).all()
    menu_count = sum(1 for row in rows if row.perm_type == "menu")
    api_count = sum(1 for row in rows if row.perm_type == "api")
    return PermissionTreeResponse(
        tree=build_permission_tree(rows),
        menu_count=menu_count,
        api_count=api_count,
    )
