from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_access_token
from app.database import SessionLocal
from app.models import Role, User

_bearer = HTTPBearer(auto_error=False)


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
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    try:
        payload = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效") from exc
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    user = (
        db.query(User)
        .options(joinedload(User.role).joinedload(Role.permissions))
        .filter(User.id == user_id)
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不可用")
    if not user.role.status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="角色已禁用")
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
