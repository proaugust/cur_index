import logging
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models import User
from app.services.ops.llm_usage_service import bind_llm_usage_user_id, reset_llm_usage_user_id

logger = logging.getLogger(__name__)


def is_super_admin(user: User) -> bool:
    return user.role.level <= 1


def user_permission_codes(user: User) -> set[str]:
    return {p.code for p in user.role.permissions}


def require_permission(code: str, *, name: str | None = None, parent_code: str | None = None):
    async def checker(user: User = Depends(get_current_user)) -> AsyncGenerator[User, None]:
        token = bind_llm_usage_user_id(user.id)
        try:
            if is_super_admin(user):
                yield user
                return
            if code not in user_permission_codes(user):
                logger.warning(
                    "权限拒绝 user_id=%s username=%s role=%s code=%s",
                    user.id,
                    user.username,
                    user.role.name if user.role else None,
                    code,
                )
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"缺少权限: {code}")
            yield user
        finally:
            reset_llm_usage_user_id(token)

    checker.permission_code = code  # type: ignore[attr-defined]
    checker.permission_name = name or code  # type: ignore[attr-defined]
    checker.permission_parent_code = parent_code or code.split(".", 1)[0]  # type: ignore[attr-defined]
    return checker
