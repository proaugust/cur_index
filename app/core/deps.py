import logging
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_access_token
from app.database import SessionLocal
from app.models import Role, User
from app.services.llm_usage_service import set_llm_usage_user_id

_bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        logger.warning("鉴权失败: 未登录")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        logger.warning("鉴权失败: 登录已失效（token 无效）")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效") from exc
    user_id = payload.get("user_id")
    if not user_id:
        logger.warning("鉴权失败: 登录已失效（payload 无 user_id）")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    user = (
        db.query(User)
        .options(joinedload(User.role).joinedload(Role.permissions))
        .filter(User.id == user_id)
        .first()
    )
    if not user or not user.is_active:
        logger.warning("鉴权失败: 账号不可用 user_id=%s", user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    if not user.role.status:
        logger.warning("鉴权失败: 角色已禁用 user_id=%s username=%s role=%s", user.id, user.username, user.role.name)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="角色已禁用")
    set_llm_usage_user_id(user.id)
    return user


def get_document_import_service(db: Session = Depends(get_db)):
    from app.services.document_import_service import DocumentImportService

    return DocumentImportService(db)


def get_complaint_service(db: Session = Depends(get_db)):
    from app.services.complaint_service import ComplaintService

    return ComplaintService(db)


def get_document_search_service(db: Session = Depends(get_db)):
    from app.services.document_search_service import DocumentSearchService

    return DocumentSearchService(db)
