"""登录记录：成功登录写入；失败不影响主流程。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import LoginLog

logger = logging.getLogger(__name__)


def record_login_log(
    *,
    user_id: int | None,
    username: str,
    ip: str = "",
    user_agent: str | None = None,
) -> None:
    db = SessionLocal()
    try:
        db.add(
            LoginLog(
                user_id=user_id,
                username=(username or "")[:50],
                ip=(ip or "")[:64],
                user_agent=(user_agent[:512] if user_agent else None),
            )
        )
        db.commit()
    except Exception:
        logger.exception("登录记录写入失败 username=%s", username)
        db.rollback()
    finally:
        db.close()


def query_login_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    username: str | None = None,
    days: int | None = None,
) -> tuple[list[LoginLog], int]:
    query = db.query(LoginLog)
    if username:
        query = query.filter(LoginLog.username.ilike(f"%{username}%"))
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(LoginLog.created_at >= since)
    total = query.count()
    rows = (
        query.order_by(LoginLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total
