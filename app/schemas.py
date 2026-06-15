from typing import Literal

from pydantic import BaseModel, Field


class ItemBase(BaseModel):
    title: str


class ItemCreate(ItemBase):
    pass


class ItemRead(ItemBase):
    id: int

    model_config = {"from_attributes": True}


class DocumentImportResult(BaseModel):
    source_file: str
    sections: int
    chunks: int


class DocumentChunkRead(BaseModel):
    id: int
    source_file: str
    section_title: str
    section_path: str
    chunk_index: int
    content: str
    char_count: int

    model_config = {"from_attributes": True}


class DocumentChunkSearchResult(DocumentChunkRead):
    similarity: float


class DocumentSearchPolishedSource(BaseModel):
    snippet_index: int = Field(description="片段编号，与 polished_answer 中〔片段N〕对应")
    id: int = Field(description="document_chunks 表主键")
    source_file: str = Field(description="原始文件名")
    source_label: str = Field(description="来源展示名：文件名 + 章节")
    section_title: str
    section_path: str
    chunk_index: int
    content: str = Field(description="数据库中的原始文本片段")
    char_count: int
    similarity: float = Field(description="与查询的向量相似度，越高越相关")

    model_config = {"from_attributes": True}


class DocumentSearchPolishedResult(BaseModel):
    query: str
    polished_answer: str = Field(description="大模型综合所有片段后生成的丰富回答（Markdown）")
    source_count: int = Field(description="参与润色的原始片段数量")
    original_sources: list[DocumentSearchPolishedSource] = Field(
        description="检索到的原始资料，供前端展示出处与原文对照"
    )


class DocumentAnalyzeRequest(BaseModel):
    source_files: list[str] | None = Field(
        default=None,
        description="要分析的文档文件名列表；为空则分析库中全部文档",
    )
    report_type: Literal["risk", "summary"] = Field(
        default="risk",
        description="risk=风险分析报告，summary=多文档综合摘要",
    )
    topic: str | None = Field(
        default=None,
        description="可选关注点，如「供应链合规」「数据安全」",
    )
    chunks_per_query: int = Field(default=5, ge=1, le=20, description="每条检索 query 取 top-k 片段")


class DocumentRiskItem(BaseModel):
    title: str = Field(description="风险项标题")
    severity: Literal["高", "中", "低"] = Field(description="风险等级")
    description: str = Field(description="风险说明")
    source_file: str = Field(description="主要来源文档")
    snippet_indices: list[int] = Field(
        default_factory=list,
        description="依据片段编号，与 original_sources 中 snippet_index 对应",
    )


class DocumentAnalyzeResult(BaseModel):
    report_type: str
    source_files: list[str] = Field(description="实际参与分析的文档列表")
    topic: str | None
    report_markdown: str = Field(description="完整分析报告（Markdown）")
    risks: list[DocumentRiskItem] = Field(
        default_factory=list,
        description="结构化风险清单，仅 report_type=risk 时有值",
    )
    source_count: int
    original_sources: list[DocumentSearchPolishedSource] = Field(
        description="分析过程中检索到的全部原始片段"
    )


class ComplaintCategoryRead(BaseModel):
    id: int
    name: str
    description: str
    seed_phrases: str

    model_config = {"from_attributes": True}


class ComplaintRead(BaseModel):
    id: int
    content: str
    category_id: int | None
    category_name: str | None = None
    similarity: float | None

    model_config = {"from_attributes": True}


class ComplaintStatsItem(BaseModel):
    category_id: int
    category_name: str
    count: int
    percentage: float


class ComplaintStatsReport(BaseModel):
    total: int
    classified: int
    unclassified: int
    categories: list[ComplaintStatsItem]


class ComplaintSeedResult(BaseModel):
    inserted: int


class ComplaintClassifyResult(BaseModel):
    classified: int
    logistics_delay_count: int
    logistics_delay_percentage: float
