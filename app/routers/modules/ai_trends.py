"""HTTP 路由：全球 AI 发展趋势与智能演进数据分析。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.permissions import require_permission
from app.models import User
from app.services.modules.ai_trends_service import ai_trends_service

router = APIRouter(prefix="/ai-trends", tags=["ai-trends"])


@router.get("/stats")
def get_ai_trends_stats(
    _: User = Depends(require_permission("0", name="系统首页")),
) -> dict:
    """获取全球 AI 发展趋势与智能演进的缓存统计数据。"""
    return ai_trends_service.get_cached_stats()
