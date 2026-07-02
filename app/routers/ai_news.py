from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services import ai_news_prefs_service

router = APIRouter(prefix="/ai-news", tags=["ai-news"])


@router.get("/prefs", response_model=schemas.AiNewsUserPrefsRead)
def get_ai_news_prefs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("80.prefs")),
) -> schemas.AiNewsUserPrefsRead:
    return ai_news_prefs_service.get_user_prefs(db, current_user.id)


@router.put("/prefs", response_model=schemas.AiNewsUserPrefsRead)
def upsert_ai_news_prefs(
    body: schemas.AiNewsUserPrefsBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("80.prefs")),
) -> schemas.AiNewsUserPrefsRead:
    return ai_news_prefs_service.upsert_user_prefs(db, current_user.id, body)
