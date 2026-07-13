"""HTTP 路由：Epoch AI 数据分析。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app import schemas
from app.core.permissions import require_permission
from app.models import User
from app.services.modules.epoch_service import epoch_service

router = APIRouter(prefix="/epoch", tags=["epoch"])


@router.get("/stats")
def get_epoch_stats(
    _: User = Depends(require_permission("0", name="系统首页")),
) -> dict:
    """获取 Epoch AI 的全量模型分析统计缓存数据。"""
    return epoch_service.get_cached_stats()
