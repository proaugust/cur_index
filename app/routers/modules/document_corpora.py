"""业务知识库 API：document_business_chunks 导入 / 列文件 / 检索 / 清空 / 删库 / 切块 CRUD。"""

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.crud import document_corpora as corpus_crud
from app.models import User
from app.services.modules.chunk_lang import resolve_lang
from app.services.modules.corpus_categories import list_category_options, normalize_category, suggest_category
from app.services.modules.corpus_import_io import derive_corpus_name
from app.services.modules.corpus_import_jobs import create_import_job, get_import_job, run_import_job
from app.services.modules.corpus_search_filters import split_csv
from app.services.modules.corpus_search_service import CorpusSearchService
from app.services.shared.embedding import embed_text
from app.services.shared.structure_chunker import DEFAULT_MAX_CHUNK, DEFAULT_MIN_CHUNK, DEFAULT_OVERLAP

router = APIRouter(prefix="/documents/corpora", tags=["documents-corpora"])


def _search_service(db: Session = Depends(get_db)) -> CorpusSearchService:
    return CorpusSearchService(db)


def _require_corpus(db: Session, corpus_name: str):
    corpus = corpus_crud.get_corpus_by_name(db, corpus_name)
    if corpus is None:
        raise HTTPException(status_code=404, detail=f"资料库不存在: {corpus_name}")
    return corpus


@router.get("/categories", response_model=list[schemas.CorpusCategoryOption], summary="资料库分类枚举")
def list_corpus_categories(
    _: User = Depends(require_permission("82.corpora-list", name="资料库列表")),
) -> list[schemas.CorpusCategoryOption]:
    return [schemas.CorpusCategoryOption(**item) for item in list_category_options()]


@router.get(
    "/categories/suggest",
    response_model=schemas.CorpusCategorySuggestResult,
    summary="根据问题推荐资料分类",
)
def suggest_corpus_category(
    q: str = Query(..., min_length=1, description="用户问题"),
    _: User = Depends(require_permission("82.corpora-search", name="资料库检索")),
) -> schemas.CorpusCategorySuggestResult:
    return schemas.CorpusCategorySuggestResult(**suggest_category(q))


@router.get("", response_model=list[schemas.DocumentCorpusRead], summary="列出业务知识库")
def list_corpora(
    category: str | None = Query(default=None, description="按分类过滤，如 policy / product"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-list", name="资料库列表")),
) -> list[schemas.DocumentCorpusRead]:
    if category and category.strip():
        raw = category.strip().lower()
        normalized = normalize_category(raw)
        if normalized != raw:
            return []
        return corpus_crud.list_corpora(db, category=normalized)
    return corpus_crud.list_corpora(db)


@router.get(
    "/import/jobs/{job_id}",
    response_model=schemas.CorpusImportJobStatus,
    summary="查询资料库异步导入任务",
)
def get_corpus_import_job(
    job_id: str,
    _: User = Depends(require_permission("82.corpora-import", name="资料库导入")),
) -> schemas.CorpusImportJobStatus:
    job = get_import_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
    return schemas.CorpusImportJobStatus(**job)


@router.post(
    "/import",
    response_model=schemas.CorpusImportJobAccepted,
    summary="导入到业务知识库（异步）",
)
async def import_corpus(
    background_tasks: BackgroundTasks,
    corpus_name: str | None = Form(
        default=None,
        description="资料库名；留空则 ZIP 内顶级文件夹名 / 上传文件名（去扩展名）/ 本机目录名",
    ),
    file: UploadFile | None = File(
        default=None,
        description="单文件 .md/.txt 或 .zip（推荐；与 folder_path 二选一）",
    ),
    folder_path: str | None = Form(
        default=None,
        description="仅本地调试：服务端本机文件夹绝对路径（生产请用上传）",
    ),
    replace_existing: bool = Form(True, description="覆盖同文件名已有切块"),
    chunk_strategy: str = Form("structure", description="structure | legacy"),
    category: str = Form("other", description="资料分类：policy/product/support/legal/report/other"),
    max_chunk_len: int = Form(DEFAULT_MAX_CHUNK, ge=50, le=2000),
    min_chunk_len: int = Form(DEFAULT_MIN_CHUNK, ge=20, le=1000),
    chunk_overlap: int = Form(DEFAULT_OVERLAP, ge=0, le=500),
    _: User = Depends(require_permission("82.corpora-import", name="资料库导入")),
) -> schemas.CorpusImportJobAccepted:
    file_name = None
    file_text = None
    file_bytes = None
    if file is not None and file.filename:
        file_name = file.filename
        raw = await file.read()
        if file_name.lower().endswith(".zip"):
            file_bytes = raw
        else:
            try:
                file_text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise HTTPException(status_code=400, detail="文件编码必须是 UTF-8") from exc

    has_upload = bool(file_name and (file_text is not None or file_bytes is not None))
    has_folder = bool(folder_path and folder_path.strip())
    if not has_upload and not has_folder:
        raise HTTPException(status_code=400, detail="请上传 .md/.txt/.zip，或填写本机 folder_path")

    resolved_name = (corpus_name or "").strip() or derive_corpus_name(
        file_name=file_name,
        folder_path=folder_path,
        zip_bytes=file_bytes,
    )
    params = {
        "corpus_name": resolved_name,
        "file_name": file_name,
        "file_text": file_text,
        "file_bytes": file_bytes,
        "folder_path": folder_path,
        "replace_existing": replace_existing,
        "chunk_strategy": chunk_strategy,
        "category": normalize_category(category),
        "min_chunk_len": min_chunk_len,
        "max_chunk_len": max_chunk_len,
        "chunk_overlap": chunk_overlap,
    }
    job_id = create_import_job(corpus_name=resolved_name)
    background_tasks.add_task(run_import_job, job_id, params)
    return schemas.CorpusImportJobAccepted(job_id=job_id)


@router.get("/files", response_model=schemas.CorpusFileListResult, summary="资料库内文件名列表")
def list_corpus_files(
    corpus_name: str | None = Query(None, description="资料名（留空查全部资料库）"),
    service: CorpusSearchService = Depends(_search_service),
    _: User = Depends(require_permission("82.corpora-files", name="资料库文件列表")),
) -> schemas.CorpusFileListResult:
    return service.list_files(corpus_name)


@router.get(
    "/listByFile",
    response_model=schemas.SourceFileListPage,
    summary="资料库按文件名查（仅文件路径）",
)
def list_corpus_by_file(
    corpus_name: str | None = Query(None, description="资料名（留空查全部资料库）"),
    source_file: str | None = Query(
        default=None, description="按文件名过滤（子串匹配；含 % / _ 时为 SQL LIKE）"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: CorpusSearchService = Depends(_search_service),
    _: User = Depends(require_permission("82.corpora-listByFile", name="资料库按文件名查")),
) -> schemas.SourceFileListPage:
    return service.list_by_file(
        corpus_name, source_file=source_file, page=page, page_size=page_size
    )


@router.delete("", response_model=schemas.CorpusClearResult, summary="清空资料库切块数据")
def clear_corpus(
    corpus_name: str = Query(..., description="资料名"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-clear", name="资料库清空")),
) -> schemas.CorpusClearResult:
    """只删该资料名切块，保留 document_corpora 注册与共享表 document_business_chunks。"""
    from app.services.modules.chunk_table_ops import BUSINESS_CHUNK_TABLE

    corpus = _require_corpus(db, corpus_name)
    deleted = corpus_crud.clear_all_chunks(db, corpus.name)
    return schemas.CorpusClearResult(
        corpus_name=corpus.name,
        table_name=BUSINESS_CHUNK_TABLE,
        deleted_chunks=deleted,
    )


@router.delete("/drop", response_model=schemas.CorpusDeleteResult, summary="删除资料库（注册+切块）")
def drop_corpus(
    corpus_name: str = Query(..., description="资料名"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-delete", name="资料库删除")),
) -> schemas.CorpusDeleteResult:
    corpus = _require_corpus(db, corpus_name)
    name = corpus.name
    table_name, deleted = corpus_crud.delete_corpus(db, corpus)
    return schemas.CorpusDeleteResult(
        corpus_name=name,
        table_name=table_name,
        deleted_chunks=deleted,
    )


@router.post("/chunks", response_model=schemas.DocumentChunkRead, summary="资料库新增切块")
def create_corpus_chunk(
    payload: schemas.CorpusChunkCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-chunks-create", name="资料库新增切块")),
) -> schemas.DocumentChunkRead:
    corpus = _require_corpus(db, payload.corpus_name)
    lang = resolve_lang(payload.lang, payload.content)
    embedding = embed_text(payload.content)
    row = corpus_crud.create_chunk(
        db,
        corpus.name,
        source_file=payload.source_file,
        content=payload.content,
        section_title=payload.section_title,
        section_path=payload.section_path,
        chunk_index=payload.chunk_index,
        embedding=embedding,
        lang=lang,
    )
    return row


@router.put("/chunks/{chunk_id}", response_model=schemas.DocumentChunkRead, summary="资料库更新切块")
def update_corpus_chunk(
    chunk_id: int,
    payload: schemas.DocumentChunkUpdate,
    corpus_name: str = Query(..., description="资料名"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-chunks-update", name="资料库更新切块")),
) -> schemas.DocumentChunkRead:
    corpus = _require_corpus(db, corpus_name)
    row = corpus_crud.get_chunk_by_id(db, corpus.name, chunk_id)
    if row is None:
        raise HTTPException(status_code=404, detail="切块不存在")
    if payload.content is None and payload.section_title is None and payload.section_path is None:
        raise HTTPException(status_code=400, detail="至少提供一个待更新字段")
    embedding = None
    char_count = None
    lang = None
    if payload.content is not None:
        char_count = len(payload.content)
        embedding = embed_text(payload.content)
        lang = resolve_lang(None, payload.content)
    return corpus_crud.update_chunk(
        db,
        row,
        content=payload.content,
        section_title=payload.section_title,
        section_path=payload.section_path,
        char_count=char_count,
        embedding=embedding,
        lang=lang,
    )


@router.delete("/chunks/{chunk_id}", summary="资料库删除切块")
def delete_corpus_chunk(
    chunk_id: int,
    corpus_name: str = Query(..., description="资料名"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-chunks-delete", name="资料库删除切块")),
) -> dict[str, int | str]:
    corpus = _require_corpus(db, corpus_name)
    if corpus_crud.get_chunk_by_id(db, corpus.name, chunk_id) is None:
        raise HTTPException(status_code=404, detail="切块不存在")
    corpus_crud.delete_chunk_by_id(db, corpus.name, chunk_id)
    return {"id": chunk_id, "message": "已删除"}


@router.get(
    "/search/suggest-filters",
    response_model=schemas.CorpusSearchFiltersSuggest,
    summary="根据问题建议检索过滤条件（规则）",
)
def suggest_corpus_search_filters(
    q: str = Query(..., min_length=1, description="用户问题"),
    service: CorpusSearchService = Depends(_search_service),
    _: User = Depends(require_permission("82.corpora-search", name="资料库检索")),
) -> schemas.CorpusSearchFiltersSuggest:
    return service.suggest_filters(q)


@router.get(
    "/search",
    response_model=list[schemas.DocumentChunkSearchResult],
    summary="业务知识库检索（vector / hybrid）",
)
def search_corpus(
    corpus_name: str | None = Query(None, description="资料名（单库；与 corpus_names 并存时取并集）"),
    corpus_names: str | None = Query(None, description="多资料库名，逗号分隔"),
    categories: str | None = Query(None, description="多分类，逗号分隔；展开为资料库后与 corpus_names 并集"),
    q: str | None = Query(default=None, description="查询文本"),
    limit: int = Query(default=5, ge=1, le=50),
    min_similarity: float = Query(default=0.35, ge=0.0, le=1.0),
    source_file: str | None = Query(
        default=None, description="可选：按文件名过滤（子串匹配；含 % / _ 时为 SQL LIKE）"
    ),
    retrieve_mode: str = Query(
        default="hybrid",
        description="vector | hybrid | hybrid_rerank（hybrid=向量+全文+C1融合）",
    ),
    expand_parent: bool = Query(default=False, description="按 section_path 扩同节上下文"),
    service: CorpusSearchService = Depends(_search_service),
    _: User = Depends(require_permission("82.corpora-search", name="资料库检索")),
) -> list[schemas.DocumentChunkSearchResult]:
    return service.search(
        corpus_name,
        q,
        limit=limit,
        source_file=source_file,
        min_similarity=min_similarity,
        retrieve_mode=retrieve_mode,
        expand_parent=expand_parent,
        corpus_names=split_csv(corpus_names),
        categories=split_csv(categories),
    )


@router.get(
    "/search_and_llm",
    response_model=schemas.DocumentSearchPolishedResult,
    summary="业务知识库检索 + LLM 润色",
)
def search_corpus_and_llm(
    corpus_name: str | None = Query(None, description="资料名（留空检索全部资料库）"),
    corpus_names: str | None = Query(None, description="多资料库名，逗号分隔"),
    categories: str | None = Query(None, description="多分类，逗号分隔"),
    q: str | None = Query(default=None, description="查询文本"),
    limit: int = Query(default=5, ge=1, le=50),
    min_similarity: float = Query(default=0.35, ge=0.0, le=1.0),
    source_file: str | None = Query(default=None, description="可选文件名过滤"),
    retrieve_mode: str = Query(
        default="hybrid",
        description="vector | hybrid | hybrid_rerank",
    ),
    expand_parent: bool = Query(default=True, description="LLM 路径默认扩 Parent"),
    service: CorpusSearchService = Depends(_search_service),
    _: User = Depends(require_permission("82.corpora-search-llm", name="资料库检索+LLM")),
) -> schemas.DocumentSearchPolishedResult:
    return service.search_polished(
        corpus_name,
        q,
        limit=limit,
        min_similarity=min_similarity,
        retrieve_mode=retrieve_mode,
        expand_parent=expand_parent,
        source_file=source_file,
        corpus_names=split_csv(corpus_names),
        categories=split_csv(categories),
    )
