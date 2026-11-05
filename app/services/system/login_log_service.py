"""登录记录与页面浏览：写入失败不影响主流程。"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import Integer, String, cast, literal, null, union_all
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import LoginLog, PageView, UserAction
from app.services.system.api_access_stat_service import normalize_path

logger = logging.getLogger(__name__)

_SKIP_PAGE_PATHS = frozenset({"/", "/login", "/register", "/reset-pwd", "/403", "/404"})
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_SKIP_ACTION_EXACT = frozenset(
    {"/health", "/health/db", "/db-test", "/docs", "/redoc", "/openapi.json", "/favicon.ico", "/"}
)
_SKIP_ACTION_PREFIX = ("/assets", "/static")
_PAGE_VIEW_DEDUPE = timedelta(seconds=8)

_BROWSER_TOKENS = (
    ("Edg/", "Edge"),
    ("OPR/", "Opera"),
    ("Opera/", "Opera"),
    ("Firefox/", "Firefox"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)


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


def _major_version(ua: str, token: str) -> str:
    index = ua.find(token)
    if index < 0:
        return ""
    raw = ua[index + len(token) :].split(" ", 1)[0].split(".", 1)[0]
    return raw if raw.isdigit() else ""


def summarize_user_agent(user_agent: str | None) -> tuple[str, str]:
    """从 User-Agent 拆出「浏览器 主版本」和操作系统，解析失败时返回空字符串。"""
    ua = user_agent or ""
    browser = ""
    for token, name in _BROWSER_TOKENS:
        if token in ua:
            version_token = "Version/" if name == "Safari" and "Version/" in ua else token
            version = _major_version(ua, version_token)
            browser = f"{name} {version}".strip()
            break
    os_name = ""
    if "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "CrOS" in ua:
        os_name = "ChromeOS"
    elif "Linux" in ua:
        os_name = "Linux"
    return browser, os_name


def _normalize_page_path(path: str) -> str | None:
    raw = (path or "").strip()
    if "?" in raw:
        raw = raw.split("?", 1)[0]
    if "#" in raw:
        raw = raw.split("#", 1)[0]
    if not raw.startswith("/") or raw.startswith("//") or raw in _SKIP_PAGE_PATHS:
        return None
    return raw[:200]


def record_page_view(*, user_id: int, username: str, path: str, title: str | None = None) -> None:
    normalized = _normalize_page_path(path)
    if normalized is None:
        return
    page_title = (title or "").strip()[:100] or None
    db = SessionLocal()
    try:
        latest = (
            db.query(PageView)
            .filter(PageView.user_id == user_id, PageView.path == normalized)
            .order_by(PageView.id.desc())
            .first()
        )
        if latest is not None and datetime.utcnow() - latest.created_at < _PAGE_VIEW_DEDUPE:
            return
        db.add(
            PageView(
                user_id=user_id,
                username=(username or "")[:50],
                path=normalized,
                title=page_title,
            )
        )
        db.commit()
    except Exception:
        logger.exception("页面浏览写入失败 user_id=%s path=%s", user_id, normalized)
        db.rollback()
    finally:
        db.close()


def query_page_views(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    username: str | None = None,
    days: int | None = None,
) -> tuple[list[PageView], int]:
    query = db.query(PageView)
    if username:
        query = query.filter(PageView.username.ilike(f"%{username}%"))
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(PageView.created_at >= since)
    total = query.count()
    rows = (
        query.order_by(PageView.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def _should_record_action(method: str, path: str, user_id: int | None) -> bool:
    if user_id is None or method not in _WRITE_METHODS:
        return False
    raw = path or ""
    if raw in _SKIP_ACTION_EXACT or raw.startswith(_SKIP_ACTION_PREFIX):
        return False
    if "login-logs/page-views" in raw:
        return False
    return True


def _clean_page(page: str | None) -> str | None:
    raw = (page or "").strip()
    if "?" in raw:
        raw = raw.split("?", 1)[0]
    if not raw.startswith("/") or raw.startswith("//"):
        return None
    return raw[:200]


def record_user_action(
    *,
    user_id: int,
    username: str,
    method: str,
    path: str,
    status_code: int,
    error: str | None = None,
    page: str | None = None,
    request_id: str | None = None,
) -> None:
    if not _should_record_action(method, path, user_id):
        return
    detail = (error or "").strip()[:200] or None
    rid = (request_id or "").strip()[:32] or None
    db = SessionLocal()
    try:
        db.add(
            UserAction(
                user_id=user_id,
                username=(username or "")[:50],
                method=method[:16],
                path=normalize_path(path),
                status_code=status_code,
                error=detail,
                page=_clean_page(page),
                request_id=rid,
            )
        )
        db.commit()
    except Exception:
        logger.exception("用户操作写入失败 user_id=%s %s %s", user_id, method, path)
        db.rollback()
    finally:
        db.close()


def query_activity(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    username: str | None = None,
    days: int | None = None,
) -> tuple[list, int]:
    """页面浏览与写操作按时间倒序合并。"""

    def _null_str():
        return cast(null(), String)

    def _null_int():
        return cast(null(), Integer)

    pages = db.query(
        literal("page").label("kind"),
        PageView.username.label("username"),
        literal("").label("method"),
        PageView.path.label("path"),
        PageView.title.label("title"),
        _null_int().label("status_code"),
        _null_str().label("error"),
        _null_str().label("page"),
        _null_str().label("request_id"),
        PageView.created_at.label("created_at"),
    )
    actions = db.query(
        literal("action").label("kind"),
        UserAction.username.label("username"),
        UserAction.method.label("method"),
        UserAction.path.label("path"),
        _null_str().label("title"),
        UserAction.status_code.label("status_code"),
        UserAction.error.label("error"),
        UserAction.page.label("page"),
        UserAction.request_id.label("request_id"),
        UserAction.created_at.label("created_at"),
    )
    if username:
        like = f"%{username}%"
        pages = pages.filter(PageView.username.ilike(like))
        actions = actions.filter(UserAction.username.ilike(like))
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        pages = pages.filter(PageView.created_at >= since)
        actions = actions.filter(UserAction.created_at >= since)
    combined = union_all(pages.statement, actions.statement).subquery()
    total = db.query(combined).count()
    rows = (
        db.query(combined)
        .order_by(combined.c.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total
