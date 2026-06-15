from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.deps import get_db

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=list[schemas.ItemRead])
def list_items(db: Session = Depends(get_db)) -> list[schemas.ItemRead]:
    return crud.get_items(db)


@router.post("/", response_model=schemas.ItemRead)
def create_item(
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
) -> schemas.ItemRead:
    return crud.create_item(db, item)
