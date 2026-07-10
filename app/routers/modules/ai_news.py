from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.modules import ai_news_service

router = APIRouter(prefix="/ai-news", tags=["ai-news"])


@router.get("/board", response_model=schemas.AiNewsBoardResponse)
def get_ai_news_board(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("80.prefs", name="资讯导航")),
) -> schemas.AiNewsBoardResponse:
    return ai_news_service.get_board(db, current_user.id)


@router.put("/board", response_model=schemas.AiNewsBoardResponse)
def save_ai_news_board(
    body: schemas.AiNewsBoardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("80.prefs", name="资讯导航")),
) -> schemas.AiNewsBoardResponse:
    return ai_news_service.save_board(db, current_user.id, body)


@router.post("/links", response_model=schemas.AiNewsBoardResponse)
def create_ai_news_link(
    body: schemas.AiNewsLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("80.prefs", name="资讯导航")),
) -> schemas.AiNewsBoardResponse:
    try:
        return ai_news_service.create_custom_link(db, current_user.id, body.url)
    except ValueError as exc:
        code = str(exc)
        if code == "invalid_url":
            raise HTTPException(status_code=400, detail="请输入有效的网址") from exc
        if code == "duplicate_url":
            raise HTTPException(status_code=409, detail="该链接已存在") from exc
        raise HTTPException(status_code=400, detail="无法添加链接") from exc
