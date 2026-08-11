from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models import User
from app.schemas.rbac import ChangePasswordRequest, LoginRequest, LoginResponse, MeResponse
from app.services.system import rbac_service
from app.services.system.login_log_service import record_login_log

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()[:64]
    if request.client and request.client.host:
        return request.client.host[:64]
    return ""


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    result = rbac_service.login(db, payload)
    record_login_log(
        user_id=result.user.id,
        username=result.user.username,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return result


@router.get("/me", response_model=MeResponse)
def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return rbac_service.get_me(current_user)


@router.put("/password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    rbac_service.change_password(db, current_user, payload)
