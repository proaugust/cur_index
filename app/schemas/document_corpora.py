"""业务知识库 schemas（切块表 document_business_chunks）。"""

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
    lang: str = "zh"
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


class CorpusDeleteResult(BaseModel):
    corpus_name: str
    table_name: str
    deleted_chunks: int


class CorpusChunkCreate(BaseModel):
    corpus_name: str = Field(min_length=1, description="资料名")
    source_file: str = Field(min_length=1, description="来源文件名")
    content: str = Field(min_length=1, description="切块正文，入库时自动计算向量")
    section_title: str = Field(default="", description="章节标题")
    section_path: str = Field(default="", description="章节路径")
    chunk_index: int | None = Field(default=None, ge=0, description="块序号；留空则自动递增")
    lang: str | None = Field(default=None, description="可选；留空则按正文自动判断")
