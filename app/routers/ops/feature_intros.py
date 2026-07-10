from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas
from app.crud import modules as crud
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User

router = APIRouter(prefix="/feature-intros", tags=["feature-intros"])


@router.get("/", response_model=list[schemas.FeatureIntroRead])
def list_feature_intros(
    page_key: str | None = Query(default=None, description="按页面过滤，如 complaints、agent"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("8.feature-intros-list", name="功能介绍列表")),
) -> list[schemas.FeatureIntroRead]:
    return crud.list_feature_intros(db, page_key=page_key)


@router.put("/{page_key}/{section_key}", response_model=schemas.FeatureIntroRead)
def upsert_feature_intro(
    page_key: str,
    section_key: str,
    body: schemas.FeatureIntroUpsert,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("8.feature-intros-upsert", name="保存功能介绍")),
) -> schemas.FeatureIntroRead:
    return crud.upsert_feature_intro(db, page_key, section_key, body)


@router.post("/seed", response_model=list[schemas.FeatureIntroRead])
def seed_feature_intros(
    db: Session = Depends(get_db), _: User = Depends(require_permission("8.feature-intros-seed", name="初始化功能介绍"))
) -> list[schemas.FeatureIntroRead]:
    """初始化各业务 tab 占位行（仅插入缺失项，不覆盖已有内容）。"""
    return crud.seed_feature_intros(db)
