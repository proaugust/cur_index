from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.permissions import require_permission
from app.models import User
from app.schemas_rbac import RoleCreate, RoleListResponse, RolePermissionsUpdate, RoleRead, RoleUpdate
from app.services import rbac_service

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=RoleListResponse)
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RoleListResponse:
    return rbac_service.list_roles(db, current_user)


@router.post("/", response_model=RoleRead)
def create_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("12.create")),
) -> RoleRead:
    return rbac_service.create_role(db, current_user, payload)


@router.put("/{role_id}", response_model=RoleRead)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("12.update")),
) -> RoleRead:
    return rbac_service.update_role(db, current_user, role_id, payload)


@router.put("/{role_id}/permissions", response_model=RoleRead)
def update_role_permissions(
    role_id: int,
    payload: RolePermissionsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("12.permissions")),
) -> RoleRead:
    return rbac_service.update_role_permissions(db, current_user, role_id, payload)


@router.delete("/{role_id}")
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("12.delete")),
) -> dict[str, str]:
    rbac_service.delete_role(db, current_user, role_id)
    return {"message": "ok"}
