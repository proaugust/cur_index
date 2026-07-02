import json
import logging

from sqlalchemy.orm import Session

from app import schemas
from app.models import AiNewsUserPrefs

logger = logging.getLogger(__name__)


def _empty_prefs() -> schemas.AiNewsUserPrefsBody:
    return schemas.AiNewsUserPrefsBody(
        hiddenPresetIds=[],
        customLinks=[],
        favorites=[],
    )


def _parse_prefs_json(raw: str) -> schemas.AiNewsUserPrefsBody:
    try:
        data = json.loads(raw) if raw else {}
        return schemas.AiNewsUserPrefsBody.model_validate(data)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("ai_news prefs_json 解析失败，回退默认: %s", exc)
        return _empty_prefs()


def get_user_prefs(db: Session, user_id: int) -> schemas.AiNewsUserPrefsRead:
    row = db.query(AiNewsUserPrefs).filter(AiNewsUserPrefs.user_id == user_id).first()
    if not row:
        return schemas.AiNewsUserPrefsRead(**_empty_prefs().model_dump(), updated_at=None)
    body = _parse_prefs_json(row.prefs_json)
    return schemas.AiNewsUserPrefsRead(**body.model_dump(), updated_at=row.updated_at)


def upsert_user_prefs(db: Session, user_id: int, payload: schemas.AiNewsUserPrefsBody) -> schemas.AiNewsUserPrefsRead:
    prefs_json = json.dumps(payload.model_dump(), ensure_ascii=False)
    row = db.query(AiNewsUserPrefs).filter(AiNewsUserPrefs.user_id == user_id).first()
    if row:
        row.prefs_json = prefs_json
    else:
        row = AiNewsUserPrefs(user_id=user_id, prefs_json=prefs_json)
        db.add(row)
    db.commit()
    db.refresh(row)
    body = _parse_prefs_json(row.prefs_json)
    return schemas.AiNewsUserPrefsRead(**body.model_dump(), updated_at=row.updated_at)
