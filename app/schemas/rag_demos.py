"""RAG 场景演示 schemas（NL2SQL / 长文档 / Web / Agentic）。"""

from typing import Any

from pydantic import BaseModel, Field


class RagNl2sqlRequest(BaseModel):
    question: str = Field(min_length=1, description="自然语言问数")
    row_limit: int = Field(default=50, ge=1, le=200)


class RagNl2sqlResult(BaseModel):
    question: str
    schema_hits: list[dict[str, str]]
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    answer: str


class RagLongdocRequest(BaseModel):
    corpus_name: str = Field(min_length=1)
    question: str = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=20)


class RagLongdocResult(BaseModel):
    question: str
    corpus_name: str
    section_summaries: list[dict[str, str]]
    detail_hits: list[dict[str, Any]]
    answer: str


class RagWebSearchRequest(BaseModel):
    question: str = Field(min_length=1)
    count: int = Field(default=5, ge=1, le=10)


class RagWebSearchResult(BaseModel):
    question: str
    fresh_hint: bool = False
    search_mode: str = "bing"  # bing | sample
    sources: list[dict[str, str]]
    answer: str


class RagAgenticRequest(BaseModel):
    corpus_name: str = Field(min_length=1)
    question: str = Field(min_length=1)
    per_step_limit: int = Field(default=3, ge=1, le=10)


class RagAgenticResult(BaseModel):
    question: str
    corpus_name: str
    steps: list[str]
    step_results: list[dict[str, Any]]
    answer: str
