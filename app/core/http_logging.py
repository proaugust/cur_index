"""HTTP 访问日志、request_id 上下文与未捕获异常记录。"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


def _user_id_from_request(request: Request) -> int | None:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    raw = auth[7:].strip()
    if not raw:
        return None
    try:
        payload = decode_access_token(raw)
    except ValueError:
        return None
    user_id = payload.get("user_id")
    if user_id is None:
        return None
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from app.services.llm_usage_service import bind_llm_usage_user_id, reset_llm_usage_user_id

        rid = uuid.uuid4().hex[:12]
        rid_token = request_id_var.set(rid)
        uid_token = bind_llm_usage_user_id(_user_id_from_request(request))
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-Id"] = rid
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            reset_llm_usage_user_id(uid_token)
            request_id_var.reset(rid_token)
            log_fn = logger.warning if status_code >= 400 else logger.info
            log_fn(
                "request_id=%s %s %s status=%s %.1fms",
                rid,
                request.method,
                request.url.path,
                status_code,
                duration_ms,
            )


def register_exception_logging(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        from starlette.exceptions import HTTPException as StarletteHTTPException

        if isinstance(exc, StarletteHTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        logger.exception(
            "未处理异常 request_id=%s %s %s",
            get_request_id(),
            request.method,
            request.url.path,
        )
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
