"""登录用户接口访问粗统计：按用户+方法+路径汇总计数。"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ApiAccessStat, User

logger = logging.getLogger(__name__)

_SKIP_EXACT = frozenset(
    {"/health", "/health/db", "/db-test", "/docs", "/redoc", "/openapi.json", "/favicon.ico", "/"}
)
_SKIP_PREFIX = ("/assets", "/static")
_ID_SEGMENT = re.compile(r"^(\d+|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$")


def should_record(method: str, path: str, user_id: int | None) -> bool:
    if user_id is None:
        return False
    if method in {"OPTIONS", "HEAD"}:
        return False
    if path in _SKIP_EXACT or path.startswith(_SKIP_PREFIX):
        return False
    if path.rstrip("/").endswith("/api-access-stats"):
        return False
    return True


def normalize_path(path: str) -> str:
    raw = path or "/"
    if raw.startswith("/api/"):
        raw = raw[4:]
    elif raw == "/api":
        raw = "/"
    parts = [":id" if _ID_SEGMENT.match(seg) else seg[:64] for seg in raw.split("/") if seg]
    out = "/" + "/".join(parts) if parts else "/"
    return out[:200]


def maybe_record_request(method: str, path: str, user_id: int | None, status_code: int) -> None:
    if not should_record(method, path, user_id):
        return
    record_api_access(
        user_id=user_id,  # type: ignore[arg-type]
        method=method,
        path=normalize_path(path),
        status_code=status_code,
    )


def record_api_access(*, user_id: int, method: str, path: str, status_code: int) -> None:
    now = datetime.utcnow()
    db = SessionLocal()
    try:
        stmt = insert(ApiAccessStat).values(
            user_id=user_id,
            method=method[:16],
            path=path,
            hit_count=1,
            last_status=status_code,
            last_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_api_access_stats_user_method_path",
            set_={
                "hit_count": ApiAccessStat.hit_count + 1,
                "last_status": stmt.excluded.last_status,
                "last_at": stmt.excluded.last_at,
            },
        )
        db.execute(stmt)
        db.commit()
    except Exception:
        logger.exception("接口访问统计写入失败 user_id=%s %s %s", user_id, method, path)
        db.rollback()
    finally:
        db.close()


def query_api_access_stats(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    username: str | None = None,
    days: int | None = None,
) -> tuple[list[tuple[ApiAccessStat, str]], int]:
    query = db.query(ApiAccessStat, User.username).outerjoin(User, User.id == ApiAccessStat.user_id)
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))
    if days:
        query = query.filter(ApiAccessStat.last_at >= datetime.utcnow() - timedelta(days=days))
    total = query.count()
    rows = (
        query.order_by(ApiAccessStat.last_at.desc(), ApiAccessStat.hit_count.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [(row[0], row[1] or "") for row in rows], total
