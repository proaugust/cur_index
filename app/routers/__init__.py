"""HTTP 路由：按 system / demo / ops 分域聚合。"""

from fastapi import APIRouter

from app.routers.demo import (
    ai_news,
    attendance,
    chat,
    cobol_migrate,
    complaints,
    documents,
    meeting,
    my_agent,
    smart_route,
    zha_jinhua,
)
from app.routers.ops import feature_intros, llm_usage
from app.routers.system import auth, menus, permissions, roles, users


def all_routers() -> tuple[APIRouter, ...]:
    return (
        auth.router,
        users.router,
        roles.router,
        menus.router,
        permissions.router,
        documents.router,
        complaints.router,
        chat.router,
        meeting.router,
        smart_route.router,
        attendance.router,
        my_agent.router,
        cobol_migrate.router,
        feature_intros.router,
        ai_news.router,
        zha_jinhua.router,
        llm_usage.router,
    )
