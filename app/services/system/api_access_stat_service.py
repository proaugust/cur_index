"""登录用户接口访问粗统计：按用户+方法+路径汇总计数。"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ApiAccessDaily, User
from app.services.system.permission_catalog import MENU_PERMISSIONS

logger = logging.getLogger(__name__)

_ROUTE_NAMES = {
    route: name
    for _code, name, _parent, route, _icon in MENU_PERMISSIONS
    if route and route.startswith("/")
}

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
    if "/api-access-stats" in path.rstrip("/"):
        return False
    if method == "POST" and "login-logs/page-views" in path:
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


def maybe_record_request(
    method: str,
    path: str,
    user_id: int | None,
    status_code: int,
    page: str | None = None,
    tab: str | None = None,
) -> None:
    if not should_record(method, path, user_id):
        return
    record_api_access(
        user_id=user_id,  # type: ignore[arg-type]
        method=method,
        path=normalize_path(path),
        status_code=status_code,
        page=page or "",
        tab=tab or "",
    )


def record_api_access(
    *,
    user_id: int,
    method: str,
    path: str,
    status_code: int,
    page: str = "",
    tab: str = "",
) -> None:
    now = datetime.utcnow()
    db = SessionLocal()
    try:
        stmt = insert(ApiAccessDaily).values(
            user_id=user_id,
            page=(page or "")[:200],
            tab=(tab or "")[:100],
            method=method[:16],
            path=path,
            day=now.date(),
            status_code=int(status_code),
            hit_count=1,
            last_at=now,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_api_access_daily_bucket",
            set_={
                "hit_count": ApiAccessDaily.hit_count + 1,
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


def _page_clause(keyword: str):
    text = keyword.strip()
    like = f"%{text}%"
    lowered = text.lower()
    routes = [route for route, name in _ROUTE_NAMES.items() if lowered in name.lower()]
    clauses = [ApiAccessDaily.page.ilike(like), ApiAccessDaily.tab.ilike(like)]
    if routes:
        clauses.append(ApiAccessDaily.page.in_(routes))
    return or_(*clauses)


def query_api_access_stats(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    username: str | None = None,
    days: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    page_name: str | None = None,
    path: str | None = None,
    method: str | None = None,
    hit_count: int | None = None,
    status_code: int | None = None,
) -> tuple[list[dict], int]:
    hits = func.sum(ApiAccessDaily.hit_count).label("hits")
    last_at = func.max(ApiAccessDaily.last_at).label("last_at")
    query = (
        db.query(
            ApiAccessDaily.user_id,
            func.max(User.username).label("username"),
            ApiAccessDaily.page,
            ApiAccessDaily.tab,
            ApiAccessDaily.method,
            ApiAccessDaily.path,
            ApiAccessDaily.status_code,
            hits,
            last_at,
        )
        .outerjoin(User, User.id == ApiAccessDaily.user_id)
        .group_by(
            ApiAccessDaily.user_id,
            ApiAccessDaily.page,
            ApiAccessDaily.tab,
            ApiAccessDaily.method,
            ApiAccessDaily.path,
            ApiAccessDaily.status_code,
        )
    )
    if username:
        query = query.filter(User.username.ilike(f"%{username}%"))
    if days and start is None and end is None:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query = query.filter(ApiAccessDaily.day >= cutoff.date())
    if start:
        query = query.filter(ApiAccessDaily.day >= start.date())
    if end:
        query = query.filter(ApiAccessDaily.day <= end.date())
    if page_name and page_name.strip():
        query = query.filter(_page_clause(page_name))
    if path and path.strip():
        query = query.filter(ApiAccessDaily.path.ilike(f"%{path.strip()}%"))
    if method and method.strip():
        query = query.filter(ApiAccessDaily.method == method.strip().upper()[:16])
    grouped: dict[tuple, dict] = {}
    for row in query.all():
        key = (row.user_id, row.page or "", row.tab or "", row.method, row.path)
        item = grouped.get(key)
        seen = row.last_at
        count = int(row.hits or 0)
        if item is None:
            item = {
                "user_id": row.user_id,
                "username": row.username or "",
                "page": row.page or "",
                "tab": row.tab or "",
                "method": row.method,
                "path": row.path,
                "hit_count": 0,
                "statuses": {},
                "last_at": seen,
            }
            grouped[key] = item
        item["hit_count"] += count
        item["statuses"][str(row.status_code)] = int(item["statuses"].get(str(row.status_code), 0)) + count
        if seen and (item["last_at"] is None or seen > item["last_at"]):
            item["last_at"] = seen
    items = sorted(grouped.values(), key=lambda item: (item["last_at"] or datetime.min, item["hit_count"]), reverse=True)
    if hit_count is not None:
        items = [item for item in items if item["hit_count"] == hit_count]
    if status_code is not None:
        code = str(status_code)
        items = [item for item in items if code in item["statuses"]]
    if start:
        items = [item for item in items if item["last_at"] and item["last_at"] >= start]
    if end:
        items = [item for item in items if item["last_at"] and item["last_at"] <= end]
    total = len(items)
    offset = (page - 1) * page_size
    return items[offset : offset + page_size], total
