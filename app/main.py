from contextlib import asynccontextmanager
import logging
import os
import threading

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import BASE_DIR, Settings, settings
from app.database import SessionLocal, engine
from app.models import Base
from app.routers import attendance, auth, chat, cobol_migrate, complaints, documents, feature_intros, items, meeting, menus, my_agent, permissions, roles, smart_route, users, zha_jinhua
from app.services.rbac_seed import ensure_permission_schema, seed_rbac

STATIC_DIR = BASE_DIR / "static"
# 本地无 static/ 时强制开发模式，避免误设 SERVE_STATIC=1 导致 /api 与 Vite 代理冲突全 404
SERVE_STATIC = settings.serve_static and STATIC_DIR.is_dir()

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
    zha_jinhua.router,
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
    env_db = os.getenv("DATABASE_URL")
    logger.info("环境变量 DATABASE_URL: %s", "已设置" if env_db else "未设置")
    logger.info("数据库连接来源: %s", settings.database_url_source or "unknown")
    db_url = settings.database_url
    db_target = db_url.split("@")[-1] if "@" in db_url else db_url
    if "pooler_fix" in (settings.database_url_source or ""):
        logger.warning("DATABASE_URL 含 aws-0 Pooler，已自动改为 aws-1-ap-northeast-1")
    if "localhost" in db_url or "127.0.0.1" in db_url:
        logger.error(
            "DATABASE_URL 仍指向本机 (%s)。HF 请在 Space → Repository secrets 配置与本地 .env 相同的 Pooler 连接串。",
            db_target,
        )
    else:
        logger.info("数据库目标: %s", db_target)
    try:
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
    except Exception:
        logger.exception("数据库连接失败（检查 HF Secret、Supabase Pooler、Network Restrictions）")
        raise
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

if SERVE_STATIC:
    logger.info("生产布局: API 前缀 /api，托管 %s", STATIC_DIR)
    _register_api_routes(app, prefix="/api")
else:
    if settings.serve_static and not STATIC_DIR.is_dir():
        logger.warning("SERVE_STATIC=1 但无 static/ 目录，已回退为本地开发路由（无 /api 前缀）")
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

@app.get("/db-test")
async def db_test() -> dict[str, str | int]:
    """通过 Supabase 官方 SDK（PostgREST）探测连通性，不暴露连接串。"""
    cfg = Settings()  # 诊断接口每次重读 .env，避免改配置后未重启仍报未配置
    if not cfg.supabase_url or not cfg.supabase_key:
        return {"status": "fail", "error": "SUPABASE_URL / SUPABASE_KEY 未配置"}
    try:
        client = cfg.supabase_client()
        resp = client.table("users").select("id", count="exact").limit(1).execute()
        count = resp.count if resp.count is not None else len(resp.data)
        logger.info("Supabase SDK 连接成功，users 表 count=%s", count)
        return {"status": "ok", "users_count": count}
    except Exception as exc:
        logger.exception("Supabase SDK 连接失败")
        return {"status": "fail", "error": str(exc)[:300]}


@app.get("/health/db")
async def health_db() -> dict[str, str]:
    """部署诊断：不暴露连接串，仅报告能否连库。"""
    target = settings.database_url.split("@")[-1] if "@" in settings.database_url else "unknown"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"db": "ok", "target": target}
    except Exception as exc:
        return {"db": "fail", "target": target, "error": str(exc)[:300]}


if SERVE_STATIC:
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],
        reload_includes=[".env"],
    )
