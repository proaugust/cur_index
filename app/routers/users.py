from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.schemas_rbac import UserCreate, UserListResponse, UserRead, UserUpdate
from app.services import rbac_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=UserListResponse)
def list_users(
    name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("11.list")),
) -> UserListResponse:
    return rbac_service.list_users(db, current_user, name=name, page=page, page_size=page_size)


@router.post("/", response_model=UserRead)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("11.create")),
) -> UserRead:
    return rbac_service.create_user(db, current_user, payload)


@router.put("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("11.update")),
) -> UserRead:
    return rbac_service.update_user(db, current_user, user_id, payload)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("11.delete")),
) -> dict[str, str]:
    rbac_service.delete_user(db, current_user, user_id)
    return {"message": "ok"}
