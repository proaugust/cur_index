from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.schemas_rbac import MenuCreate, MenuRead, MenuUpdate
from app.services import menu_service

router = APIRouter(prefix="/menus", tags=["menus"])


@router.get("/", response_model=list[MenuRead])
def list_menus(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("13.list")),
) -> list[MenuRead]:
    return menu_service.list_menus(db, current_user)


@router.post("/", response_model=MenuRead)
def create_menu(
    payload: MenuCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("13.create")),
) -> MenuRead:
    return menu_service.create_menu(db, current_user, payload)


@router.put("/{code}", response_model=MenuRead)
def update_menu(
    code: str,
    payload: MenuUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("13.update")),
) -> MenuRead:
    return menu_service.update_menu(db, current_user, code, payload)


@router.delete("/{code}")
def delete_menu(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("13.delete")),
) -> dict[str, str]:
    menu_service.delete_menu(db, current_user, code)
    return {"message": "ok"}
