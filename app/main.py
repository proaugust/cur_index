from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.config import settings
from app.database import Base, engine
from app.routers import auth, complaints, documents, items
from app.database import SessionLocal
from app.services.document_search_service import DocumentSearchService
from app.services.embedding import warmup as warmup_embedding
from app.services.llm import warmup as warmup_llm


def _warmup() -> None:
    warmup_embedding()
    db = SessionLocal()
    try:
        DocumentSearchService(db).search("warmup", limit=1)
    finally:
        db.close()
    warmup_llm()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _warmup()
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(items.router)
app.include_router(documents.router)
app.include_router(complaints.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello, FastAPI!"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}



if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)