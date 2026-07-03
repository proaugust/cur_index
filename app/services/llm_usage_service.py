"""LLM 调用用量记录与统计。"""

from __future__ import annotations

import logging
from contextvars import ContextVar, Token
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import schemas
from app.core.http_logging import get_request_id
from app.database import SessionLocal
from app.models import LlmUsageLog, User
from app.services.llm_usage_stats_cache import get_cached_usage_stats, set_cached_usage_stats

logger = logging.getLogger(__name__)

_user_id_var: ContextVar[int | None] = ContextVar("llm_usage_user_id", default=None)


def set_llm_usage_user_id(user_id: int | None) -> None:
    _user_id_var.set(user_id)


def bind_llm_usage_user_id(user_id: int | None) -> Token | None:
    """在 async 请求上下文中绑定 user_id，返回 reset 用 token。"""
    if user_id is None:
        return None
    return _user_id_var.set(user_id)


def reset_llm_usage_user_id(token: Token | None) -> None:
    if token is not None:
        _user_id_var.reset(token)


def get_llm_usage_user_id() -> int | None:
    return _user_id_var.get()


def record_llm_usage(
    *,
    caller: str,
    engine: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    latency_ms: int,
    success: bool,
    request_id: str | None = None,
    user_id: int | None = None,
) -> None:
    rid = request_id if request_id is not None else get_request_id()
    uid = user_id if user_id is not None else get_llm_usage_user_id()
    if total_tokens <= 0 and prompt_tokens + completion_tokens > 0:
        total_tokens = prompt_tokens + completion_tokens

    logger.info(
        "LLM 用量 caller=%s user_id=%s engine=%s model=%s request_id=%s prompt=%s completion=%s total=%s %.0fms success=%s",
        caller,
        uid or "-",
        engine,
        model,
        rid,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        latency_ms,
        success,
    )

    db = SessionLocal()
    try:
        db.add(
            LlmUsageLog(
                caller=caller[:64],
                engine=engine[:16],
                model=model[:64],
                request_id=rid if rid and rid != "-" else None,
                user_id=uid,
                prompt_tokens=max(prompt_tokens, 0),
                completion_tokens=max(completion_tokens, 0),
                total_tokens=max(total_tokens, 0),
                latency_ms=max(latency_ms, 0),
                success=success,
            )
        )
        db.commit()
    except Exception:
        logger.exception("LLM 用量写入失败 caller=%s user_id=%s", caller, uid)
        db.rollback()
    finally:
        db.close()


def _display_username(user_id: int | None, username: str | None) -> str:
    if username:
        return username
    if user_id:
        return f"用户#{user_id}"
    return "未知"


def _share_percent(value: int, total: int) -> float:
    return round(value / total * 100, 2) if total else 0.0


def _apply_log_filters(
    query,
    db: Session,
    *,
    caller: str | None = None,
    username: str | None = None,
    user_id: int | None = None,
    engine: str | None = None,
    success: bool | None = None,
    request_id: str | None = None,
    days: int | None = None,
    exclude_warmup: bool = True,
):
    if exclude_warmup:
        query = query.filter(LlmUsageLog.caller != "warmup")
    if days is not None:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(LlmUsageLog.created_at >= since)
    if caller:
        query = query.filter(LlmUsageLog.caller.ilike(f"%{caller.strip()}%"))
    if user_id is not None:
        query = query.filter(LlmUsageLog.user_id == user_id)
    if username:
        query = query.filter(
            LlmUsageLog.user_id.in_(
                db.query(User.id).filter(User.username.ilike(f"%{username.strip()}%"))
            )
        )
    if engine:
        query = query.filter(LlmUsageLog.engine.ilike(f"%{engine.strip()}%"))
    if success is not None:
        query = query.filter(LlmUsageLog.success == success)
    if request_id:
        query = query.filter(LlmUsageLog.request_id.ilike(f"%{request_id.strip()}%"))
    return query


def get_usage_stats(db: Session, *, days: int | None = None, exclude_warmup: bool = True) -> dict:
    cached = get_cached_usage_stats(days=days, exclude_warmup=exclude_warmup)
    if cached is not None:
        return cached.model_dump()

    base = db.query(LlmUsageLog)
    base = _apply_log_filters(base, db, days=days, exclude_warmup=exclude_warmup)

    caller_rows = (
        base.with_entities(
            LlmUsageLog.caller,
            func.count(LlmUsageLog.id).label("calls"),
            func.coalesce(func.sum(LlmUsageLog.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(LlmUsageLog.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        )
        .group_by(LlmUsageLog.caller)
        .order_by(func.sum(LlmUsageLog.total_tokens).desc())
        .all()
    )

    user_rows = (
        base.outerjoin(User, LlmUsageLog.user_id == User.id)
        .with_entities(
            LlmUsageLog.user_id,
            User.username,
            func.count(LlmUsageLog.id).label("calls"),
            func.coalesce(func.sum(LlmUsageLog.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(LlmUsageLog.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(LlmUsageLog.total_tokens), 0).label("total_tokens"),
        )
        .group_by(LlmUsageLog.user_id, User.username)
        .order_by(func.sum(LlmUsageLog.total_tokens).desc())
        .all()
    )

    total_calls = sum(int(row.calls) for row in caller_rows)
    total_prompt = sum(int(row.prompt_tokens) for row in caller_rows)
    total_completion = sum(int(row.completion_tokens) for row in caller_rows)
    total_tokens = sum(int(row.total_tokens) for row in caller_rows)

    by_caller = [
        {
            "caller": row.caller,
            "calls": int(row.calls),
            "prompt_tokens": int(row.prompt_tokens),
            "completion_tokens": int(row.completion_tokens),
            "total_tokens": int(row.total_tokens),
            "share_percent": _share_percent(int(row.total_tokens), total_tokens),
        }
        for row in caller_rows
    ]

    by_user = [
        {
            "user_id": row.user_id,
            "username": _display_username(row.user_id, row.username),
            "calls": int(row.calls),
            "prompt_tokens": int(row.prompt_tokens),
            "completion_tokens": int(row.completion_tokens),
            "total_tokens": int(row.total_tokens),
            "share_percent": _share_percent(int(row.total_tokens), total_tokens),
        }
        for row in user_rows
    ]

    report = schemas.LlmUsageStatsResponse(
        days=days,
        total_calls=total_calls,
        total_prompt_tokens=total_prompt,
        total_completion_tokens=total_completion,
        total_tokens=total_tokens,
        by_caller=by_caller,
        by_user=by_user,
    )
    set_cached_usage_stats(days=days, exclude_warmup=exclude_warmup, report=report)
    return report.model_dump()


def query_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 200,
    caller: str | None = None,
    username: str | None = None,
    user_id: int | None = None,
    engine: str | None = None,
    success: bool | None = None,
    request_id: str | None = None,
    days: int | None = None,
    exclude_warmup: bool = True,
) -> tuple[list[dict], int]:
    base = db.query(LlmUsageLog)
    base = _apply_log_filters(
        base,
        db,
        caller=caller,
        username=username,
        user_id=user_id,
        engine=engine,
        success=success,
        request_id=request_id,
        days=days,
        exclude_warmup=exclude_warmup,
    )
    total = base.with_entities(func.count(LlmUsageLog.id)).scalar() or 0
    rows = (
        base.with_entities(LlmUsageLog, User.username)
        .outerjoin(User, LlmUsageLog.user_id == User.id)
        .order_by(LlmUsageLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        {
            "id": log.id,
            "caller": log.caller,
            "engine": log.engine,
            "model": log.model,
            "request_id": log.request_id,
            "user_id": log.user_id,
            "username": _display_username(log.user_id, username),
            "prompt_tokens": log.prompt_tokens,
            "completion_tokens": log.completion_tokens,
            "total_tokens": log.total_tokens,
            "latency_ms": log.latency_ms,
            "success": log.success,
            "created_at": log.created_at,
        }
        for log, username in rows
    ]
    return items, int(total)


def get_recent_logs(db: Session, *, limit: int = 50) -> list[dict]:
    items, _ = query_logs(db, page=1, page_size=limit)
    return items
