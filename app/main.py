from contextlib import asynccontextmanager
import logging
import threading

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import BASE_DIR, settings
from app.database import SessionLocal, engine
from app.models import Base
from app.routers import attendance, auth, chat, cobol_migrate, complaints, documents, feature_intros, items, meeting, menus, my_agent, permissions, roles, smart_route, users
from app.services.rbac_seed import ensure_permission_schema, seed_rbac

STATIC_DIR = BASE_DIR / "static"

API_ROUTERS = (
    auth.router,
    users.router,
    roles.router,
    menus.router,
    permissions.router,
    items.router,
    documents.router,
    complaints.router,
    chat.router,
    meeting.router,
    smart_route.router,
    attendance.router,
    my_agent.router,
    cobol_migrate.router,
    feature_intros.router,
)


def _configure_logging() -> None:
    """确保 app.* 日志在 F5 / uvicorn 下都能输出到终端。"""
    level = logging.DEBUG if settings.debug else logging.INFO
    if not logging.root.handlers:
        logging.basicConfig(level=level, format="%(levelname)s:     %(name)s - %(message)s")
    else:
        logging.root.setLevel(level)
    logging.getLogger("app").setLevel(level)


_configure_logging()
logger = logging.getLogger(__name__)


def _warmup_in_background() -> None:
    """后台预热重资源，不阻塞 HTTP 启动；以内存换首次请求延迟。"""
    from app.services.embedding import warmup as embedding_warmup
    from app.services.llm import warmup as llm_warmup

    try:
        embedding_warmup()
        logger.info("Embedding 模型预热完成")
    except Exception:
        logger.exception("Embedding 模型预热失败，首次向量检索可能较慢")

    try:
        llm_warmup()
        logger.info("LLM 连接预热完成")
    except Exception:
        logger.warning("LLM 预热失败，首次大模型请求可能较慢", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_permission_schema(engine)
    db = SessionLocal()
    try:
        seed_rbac(db)
        logger.info("RBAC 种子数据已就绪")
    except Exception:
        logger.exception("RBAC 种子数据初始化失败")
    finally:
        db.close()
    print(f"应用名称: {app.title}")
    threading.Thread(target=_warmup_in_background, name="app-warmup", daemon=True).start()
    yield


def _register_api_routes(app: FastAPI, *, prefix: str = "") -> None:
    if prefix:
        api_router = APIRouter(prefix=prefix)
        for router in API_ROUTERS:
            api_router.include_router(router)
        app.include_router(api_router)
    else:
        for router in API_ROUTERS:
            app.include_router(router)


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

if settings.serve_static:
    _register_api_routes(app, prefix="/api")
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_api_routes(app)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Hello, FastAPI!"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if settings.serve_static and STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],
    )
