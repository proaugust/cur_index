from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas_rbac import PermissionTreeResponse
from app.services import permission_service

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("/tree", response_model=PermissionTreeResponse)
def permission_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PermissionTreeResponse:
    return permission_service.list_permission_tree(db, current_user)
