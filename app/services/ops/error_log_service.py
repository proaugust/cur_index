"""应用错误日志：独立 session 写入，失败不影响主流程。"""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.http_logging import get_request_id
from app.database import SessionLocal
from app.models import AppErrorLog
from app.services.ops.llm_usage_service import get_llm_usage_user_id

logger = logging.getLogger(__name__)


def record_app_error(
    *,
    source: str,
    message: str,
    error_type: str = "",
    detail: str | None = None,
    level: str = "error",
    request_id: str | None = None,
    user_id: int | None = None,
    path: str | None = None,
    method: str | None = None,
    ref_type: str | None = None,
    ref_id: str | int | None = None,
    exc: BaseException | None = None,
) -> None:
    rid = request_id if request_id is not None else get_request_id()
    uid = user_id if user_id is not None else get_llm_usage_user_id()
    err_type = error_type or (exc.__class__.__name__ if exc else "")
    body = detail
    if body is None and exc is not None:
        body = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[:8000]
    db = SessionLocal()
    try:
        db.add(
            AppErrorLog(
                level=(level or "error")[:16],
                source=(source or "unknown")[:64],
                error_type=(err_type or "")[:128],
                message=(message or "")[:500],
                detail=body,
                request_id=rid if rid and rid != "-" else None,
                user_id=uid,
                path=path[:256] if path else None,
                method=method[:16] if method else None,
                ref_type=ref_type[:64] if ref_type else None,
                ref_id=None if ref_id is None else str(ref_id)[:64],
                status="open",
            )
        )
        db.commit()
    except Exception:
        logger.exception("错误日志写入失败 source=%s", source)
        db.rollback()
    finally:
        db.close()


def query_error_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    source: str | None = None,
    level: str | None = None,
    status: str | None = None,
    error_type: str | None = None,
    request_id: str | None = None,
    days: int | None = None,
) -> tuple[list[AppErrorLog], int]:
    query = db.query(AppErrorLog)
    if source:
        query = query.filter(AppErrorLog.source == source)
    if level:
        query = query.filter(AppErrorLog.level == level)
    if status:
        query = query.filter(AppErrorLog.status == status)
    if error_type:
        query = query.filter(AppErrorLog.error_type == error_type)
    if request_id:
        query = query.filter(AppErrorLog.request_id == request_id)
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AppErrorLog.created_at >= since)
    total = query.count()
    rows = (
        query.order_by(AppErrorLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def update_error_status(db: Session, error_id: int, status: str) -> AppErrorLog | None:
    row = db.get(AppErrorLog, error_id)
    if row is None:
        return None
    row.status = status
    db.commit()
    db.refresh(row)
    return row
