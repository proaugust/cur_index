"""角色权限码缓存：内存 → Redis → DB。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models import Role
from app.services.shared.memory_cache import memory_delete_by_prefix, memory_get_json, memory_set_json
from app.services.shared.redis_client import cache_delete_by_prefix, cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

_KEY_PREFIX = "rbac:role:"
PERMISSION_CODES_ATTR = "_permission_codes"


def _cache_key(role_id: int) -> str:
    return f"{_KEY_PREFIX}{role_id}:codes"


def _ttl() -> int:
    return settings.rbac_role_perms_cache_ttl


def _normalize_codes(payload: object) -> list[str] | None:
    if not isinstance(payload, list):
        return None
    codes: list[str] = []
    for item in payload:
        if not isinstance(item, str):
            return None
        codes.append(item)
    return codes


def _load_codes_from_db(db: Session, role_id: int) -> list[str]:
    role = db.query(Role).options(joinedload(Role.permissions)).filter(Role.id == role_id).first()
    if not role:
        return []
    return sorted({p.code for p in role.permissions})


def set_role_permission_codes(role_id: int, codes: list[str] | set[str]) -> None:
    key = _cache_key(role_id)
    payload = sorted(set(codes))
    ttl = _ttl()
    memory_set_json(key, payload, ttl=ttl)
    if settings.redis_enabled:
        cache_set_json(key, payload, ttl=ttl)


def get_role_permission_codes(db: Session, role_id: int) -> set[str]:
    key = _cache_key(role_id)
    memory_payload = memory_get_json(key)
    if memory_payload is not None:
        codes = _normalize_codes(memory_payload)
        if codes is not None:
            return set(codes)
        logger.warning("角色权限缓存反序列化失败 source=memory key=%s", key)

    if settings.redis_enabled:
        redis_payload = cache_get_json(key)
        if redis_payload is not None:
            codes = _normalize_codes(redis_payload)
            if codes is not None:
                memory_set_json(key, codes, ttl=_ttl())
                return set(codes)
            logger.warning("角色权限缓存反序列化失败 source=redis key=%s", key)

    codes = _load_codes_from_db(db, role_id)
    set_role_permission_codes(role_id, codes)
    return set(codes)


def attach_permission_codes(user, codes: set[str]) -> None:
    setattr(user, PERMISSION_CODES_ATTR, frozenset(codes))


def permission_codes_from_user(user) -> set[str] | None:
    cached = getattr(user, PERMISSION_CODES_ATTR, None)
    if cached is None:
        return None
    return set(cached)


def invalidate_role_permissions_cache(role_id: int | None = None) -> int:
    prefix = _KEY_PREFIX if role_id is None else f"{_KEY_PREFIX}{role_id}:"
    memory_deleted = memory_delete_by_prefix(prefix)
    redis_deleted = cache_delete_by_prefix(prefix) if settings.redis_enabled else 0
    total = memory_deleted + redis_deleted
    if total:
        logger.info("已清除角色权限缓存 role_id=%s memory=%s redis=%s", role_id, memory_deleted, redis_deleted)
    return total


def refresh_all_role_permission_caches(db: Session) -> int:
    """启动 seed / 全量刷新：一次查出所有角色权限并写入缓存。"""
    invalidate_role_permissions_cache()
    rows = db.query(Role).options(joinedload(Role.permissions)).order_by(Role.id).all()
    for role in rows:
        set_role_permission_codes(role.id, [p.code for p in role.permissions])
    logger.info("角色权限缓存已全量刷新 count=%s", len(rows))
    return len(rows)
