from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.schemas_rbac import PermissionTreeResponse
from app.services.system import permission_service

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/tree", response_model=PermissionTreeResponse)
def permission_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("12.permissions", name="分配权限")),
) -> PermissionTreeResponse:
    return permission_service.list_permission_tree(db, current_user)
