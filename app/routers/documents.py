from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.deps import get_db, get_document_import_service, get_document_search_service
from app.core.permissions import require_permission
from app.models import User
from app.services.document_import_service import DocumentImportService
from app.services.document_search_service import DocumentSearchService
from app.services.embedding import embed_text

router = APIRouter(prefix="/documents", tags=["documents"])

_SEARCH_DESC = (
    "将查询文本经 BGE 模型转为 512 维向量，在 PostgreSQL 中用 pgvector 余弦距离检索 top-k。"
    "入库与查询须使用同一 embedding 模型；更换模型后需重新导入文档。"
)
_LLM_DESC = (
    "返回两部分：① polished_answer — 将全部检索片段交给大模型综合润色后的丰富回答；"
    "② original_sources — 原始资料列表（文件名、章节、数据库 content、相似度），"
    "片段编号 snippet_index 与回答中的〔片段N〕一一对应，便于前端上下对照展示。"
    "需配置 OPENAI_API_KEY、LLM_API_BASE、LLM_MODEL。"
)


@router.post("/import", response_model=schemas.DocumentImportResult)
async def import_document(
    file: UploadFile = File(..., description="待导入的 UTF-8 文本文档"),
    replace_existing: bool = Form(True, description="是否覆盖同文件名的已有切块"),
    max_chunk_len: int = Form(300, ge=50, le=2000, description="最大切块长度（字符数上限，建议300-500）"),
    chunk_overlap: int = Form(50, ge=0, le=500, description="前后切块重叠的字符数（建议50左右）"),
    min_chunk_len: int = Form(10, ge=5, le=200, description="最小切块长度下限"),
    service: DocumentImportService = Depends(get_document_import_service),
    _: User = Depends(require_permission("82.import")),
) -> schemas.DocumentImportResult:
    if not file.filename:
        raise HTTPException(status_code=400, detail="未指定文件名")

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="文件编码必须是 UTF-8") from exc

    if max_chunk_len < min_chunk_len:
        raise HTTPException(status_code=400, detail="max_chunk_len 不能小于 min_chunk_len")

    return service.import_text(
        text,
        source_file=file.filename,
        replace_existing=replace_existing,
        min_chunk_len=min_chunk_len,
        max_chunk_len=max_chunk_len,
        chunk_overlap=chunk_overlap,
    )


@router.get("/listByFile", response_model=list[schemas.DocumentChunkRead])
def listByFile(
    source_file: str | None = Query(default=None, description="按文件名"),
    limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.listByFile")),
) -> list[schemas.DocumentChunkRead]:
    return crud.get_document_chunks(db, source_file=source_file, limit=limit)


@router.get(
    "/search",
    response_model=list[schemas.DocumentChunkSearchResult],
    summary="向量语义检索 document_chunks",
    description=_SEARCH_DESC,
)
def search(
    q: str | None = Query(default=None, description="查询文本；留空则返回库中前 limit 条切块"),
    limit: int = Query(default=5, ge=1, le=50),
    min_similarity: float = Query(default=0.65, ge=0.0, le=1.0, description="最低相似度，低于此值的结果丢弃"),
    service: DocumentSearchService = Depends(get_document_search_service),
    _: User = Depends(require_permission("82.search")),
) -> list[schemas.DocumentChunkSearchResult]:
    return service.search(q, limit=limit, min_similarity=min_similarity)


@router.get(
    "/search_and_llm",
    response_model=schemas.DocumentSearchPolishedResult,
    summary="向量检索 + 大模型润色回答",
    description=_LLM_DESC,
)
def search_and_llm(
    q: str | None = Query(default=None, description="查询文本；留空则返回库中前 limit 条切块"),
    limit: int = Query(default=5, ge=1, le=50),
    min_similarity: float = Query(default=0.65, ge=0.0, le=1.0, description="最低相似度，低于此值的结果丢弃"),
    service: DocumentSearchService = Depends(get_document_search_service),
    _: User = Depends(require_permission("82.search-and-llm")),
) -> schemas.DocumentSearchPolishedResult:
    return service.search_polished(q, limit=limit, min_similarity=min_similarity)


@router.post("/chunks", response_model=schemas.DocumentChunkRead)
def create_document_chunk(
    payload: schemas.DocumentChunkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.chunks-create")),
) -> schemas.DocumentChunkRead:
    embedding = embed_text(payload.content)
    return crud.create_document_chunk(
        db,
        source_file=payload.source_file,
        content=payload.content,
        section_title=payload.section_title,
        section_path=payload.section_path,
        chunk_index=payload.chunk_index,
        embedding=embedding,
    )


@router.put("/chunks/{chunk_id}", response_model=schemas.DocumentChunkRead)
def update_document_chunk(
    chunk_id: int, payload: schemas.DocumentChunkUpdate, db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.chunks-update")),
) -> schemas.DocumentChunkRead:
    chunk = crud.get_document_chunk_by_id(db, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="切块不存在")

    if payload.content is None and payload.section_title is None and payload.section_path is None:
        raise HTTPException(status_code=400, detail="至少提供一个待更新字段")

    embedding = None
    char_count = None
    if payload.content is not None:
        char_count = len(payload.content)
        embedding = embed_text(payload.content)

    return crud.update_document_chunk(
        db,
        chunk,
        content=payload.content,
        section_title=payload.section_title,
        section_path=payload.section_path,
        char_count=char_count,
        embedding=embedding,
    )


@router.delete("/chunks/{chunk_id}")
def delete_document_chunk(
    chunk_id: int, db: Session = Depends(get_db), _: User = Depends(require_permission("82.chunks-delete"))
) -> dict[str, int | str]:
    chunk = crud.get_document_chunk_by_id(db, chunk_id)
    if chunk is None:
        raise HTTPException(status_code=404, detail="切块不存在")

    crud.delete_document_chunk_by_id(db, chunk_id)
    return {"id": chunk_id, "message": "已删除"}
