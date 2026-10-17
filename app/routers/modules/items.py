from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.crud import modules as crud
from app.core.deps import get_db
from app.models import Item

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/list", response_model=list[schemas.ItemRead])
def list_items(db: Session = Depends(get_db)) -> list[Item]:
    return crud.get_items(db)


@router.post("/create", response_model=schemas.ItemRead)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)) -> Item:
    return crud.create_item(db, item)
