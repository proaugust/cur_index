from contextlib import asynccontextmanager
import logging
import threading

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import attendance, auth, chat, complaints, documents, feature_intros, items, meeting, my_agent, smart_route


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
    # Base.metadata.create_all(bind=engine)
    print(f"应用名称: {app.title}")
    threading.Thread(target=_warmup_in_background, name="app-warmup", daemon=True).start()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(documents.router)
app.include_router(complaints.router)
app.include_router(chat.router)
app.include_router(meeting.router)
app.include_router(smart_route.router)  # 智能路由：天气/员工/邮件分发
app.include_router(attendance.router)
app.include_router(my_agent.router)
app.include_router(feature_intros.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],
    )
