"""HTTP 访问日志、request_id 上下文与未捕获异常记录。"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()


def _identity_from_request(request: Request) -> tuple[int | None, str]:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None, ""
    raw = auth[7:].strip()
    if not raw:
        return None, ""
    try:
        payload = decode_access_token(raw)
    except ValueError:
        return None, ""
    user_id = payload.get("user_id")
    username = str(payload.get("sub") or "")[:50]
    if user_id is None:
        return None, username
    try:
        return int(user_id), username
    except (TypeError, ValueError):
        return None, username


def _user_id_from_request(request: Request) -> int | None:
    user_id, _username = _identity_from_request(request)
    return user_id


def _tab_from_request(request: Request) -> str:
    from urllib.parse import unquote

    raw = unquote(request.headers.get("x-tab") or "")
    raw = " ".join(raw.replace("\n", " ").split())
    return raw[:100]


def _page_from_request(request: Request) -> str | None:
    raw = (request.headers.get("x-page") or "").strip()
    if "?" in raw:
        raw = raw.split("?", 1)[0]
    if not raw.startswith("/") or raw.startswith("//"):
        return None
    return raw[:200]


def _error_text(raw: bytes, status_code: int) -> str | None:
    if not raw:
        return "服务器内部错误" if status_code >= 500 else None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        text = raw.decode("utf-8", errors="replace").strip()
        return (text[:200] or None) if text else ("服务器内部错误" if status_code >= 500 else None)
    detail = data.get("detail") if isinstance(data, dict) else data
    if isinstance(detail, list):
        parts: list[str] = []
        for item in detail[:3]:
            if isinstance(item, dict):
                parts.append(str(item.get("msg") or item))
            else:
                parts.append(str(item))
        text = "; ".join(part for part in parts if part)
    elif detail is None:
        text = ""
    else:
        text = str(detail).strip()
    if text:
        return text[:200]
    return "服务器内部错误" if status_code >= 500 else None


async def _error_from_response(response: Response, status_code: int) -> tuple[Response, str | None]:
    """失败响应抽出短错误。流式正文读完后重新组响应，避免客户端拿不到 body。"""
    if status_code < 400:
        return response, None
    raw = getattr(response, "body", b"") or b""
    if not isinstance(raw, (bytes, bytearray)):
        raw = b""
    if not raw and getattr(response, "body_iterator", None) is not None:
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk if isinstance(chunk, bytes) else str(chunk).encode())
        raw = b"".join(chunks)
        headers = {key: value for key, value in response.headers.items() if key.lower() != "content-length"}
        response = Response(
            content=raw,
            status_code=status_code,
            headers=headers,
            media_type=response.media_type,
        )
    return response, _error_text(bytes(raw), status_code)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from app.services.ops.llm_usage_service import bind_llm_usage_user_id, reset_llm_usage_user_id

        rid = uuid.uuid4().hex[:12]
        rid_token = request_id_var.set(rid)
        uid, username = _identity_from_request(request)
        uid_token = bind_llm_usage_user_id(uid)
        start = time.perf_counter()
        status_code = 500
        response = None
        error_text: str | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response, error_text = await _error_from_response(response, status_code)
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
            from app.services.system.api_access_stat_service import maybe_record_request
            from app.services.system.login_log_service import record_user_action

            maybe_record_request(
                request.method,
                request.url.path,
                uid,
                status_code,
                page=_page_from_request(request),
                tab=_tab_from_request(request),
            )
            if uid is not None:
                record_user_action(
                    user_id=uid,
                    username=username,
                    method=request.method,
                    path=request.url.path,
                    status_code=status_code,
                    error=error_text,
                    page=_page_from_request(request),
                    request_id=rid,
                )


def register_exception_logging(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        from starlette.exceptions import HTTPException as StarletteHTTPException

        from app.services.ops.error_log_service import record_app_error

        if isinstance(exc, StarletteHTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        logger.exception(
            "未处理异常 request_id=%s %s %s",
            get_request_id(),
            request.method,
            request.url.path,
        )
        record_app_error(
            source="http.unhandled",
            message=str(exc)[:500] or exc.__class__.__name__,
            exc=exc,
            path=str(request.url.path),
            method=request.method,
            user_id=_user_id_from_request(request),
        )
        return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})
