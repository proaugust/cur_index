from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.deps import get_db, get_document_import_service, get_document_search_service
from app.services.document_import_service import DocumentImportService
from app.services.document_search_service import DocumentSearchService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/import", response_model=schemas.DocumentImportResult)
async def import_document(
    file: UploadFile = File(..., description="待导入的 UTF-8 文本文档"),
    replace_existing: bool = Form(True, description="是否覆盖同文件名的已有切块"),
    service: DocumentImportService = Depends(get_document_import_service),
) -> schemas.DocumentImportResult:
    if not file.filename:
        raise HTTPException(status_code=400, detail="未指定文件名")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="文件编码必须是 UTF-8") from exc

    return service.import_text(text, source_file=file.filename, replace_existing=replace_existing)


@router.get("/chunks", response_model=list[schemas.DocumentChunkRead])
def list_document_chunks(
    source_file: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[schemas.DocumentChunkRead]:
    return crud.get_document_chunks(db, source_file=source_file, limit=limit)


@router.get(
    "/search",
    response_model=list[schemas.DocumentChunkSearchResult],
    summary="向量语义检索 document_chunks",
    description=(
        "将查询文本经 BGE 模型转为 512 维向量，在 PostgreSQL 中用 pgvector 余弦距离检索 top-k。"
        "入库与查询须使用同一 embedding 模型；更换模型后需重新导入文档。"
    ),
)
def search_document_chunks(
    q: str = Query(min_length=1, description="查询文本"),
    limit: int = Query(default=5, ge=1, le=50),
    service: DocumentSearchService = Depends(get_document_search_service),
) -> list[schemas.DocumentChunkSearchResult]:
    return service.search(q, limit=limit)


@router.get(
    "/search/polished",
    response_model=schemas.DocumentSearchPolishedResult,
    summary="向量检索 + 大模型润色回答",
    description=(
        "返回两部分：① polished_answer — 将全部检索片段交给大模型综合润色后的丰富回答；"
        "② original_sources — 原始资料列表（文件名、章节、数据库 content、相似度），"
        "片段编号 snippet_index 与回答中的〔片段N〕一一对应，便于前端上下对照展示。"
        "需配置 LLM_API_KEY、LLM_API_BASE、LLM_MODEL。"
    ),
)
def search_document_chunks_polished(
    q: str = Query(min_length=1, description="查询文本"),
    limit: int = Query(default=5, ge=1, le=50),
    service: DocumentSearchService = Depends(get_document_search_service),
) -> schemas.DocumentSearchPolishedResult:
    return service.search_polished(q, limit=limit)
