"""业务知识库 schemas（与旧 document_chunks 接口并存）。"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.modules import DocumentImportResult


class DocumentCorpusRead(BaseModel):
    id: int
    name: str
    table_slug: str
    table_name: str
    default_chunk_strategy: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class CorpusImportResult(BaseModel):
    corpus_name: str
    table_name: str
    files: int
    chunks: int
    details: list[DocumentImportResult] = Field(default_factory=list)


class CorpusImportJobAccepted(BaseModel):
    job_id: str
    status: Literal["pending"] = "pending"


class CorpusImportJobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "done", "failed"]
    corpus_name: str = ""
    files_done: int = 0
    files_total: int = 0
    chunks: int = 0
    error: str | None = None
    result: CorpusImportResult | dict[str, Any] | None = None


class CorpusFileItem(BaseModel):
    source_file: str


class CorpusFileListResult(BaseModel):
    corpus_name: str
    table_name: str
    files: list[CorpusFileItem]


class CorpusClearResult(BaseModel):
    corpus_name: str
    table_name: str
    deleted_chunks: int
