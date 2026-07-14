"""业务知识库 API：物理分表导入 / 列文件 / 检索 / 清空切块。"""

from typing import Union

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.crud import document_corpora as corpus_crud
from app.models import User
from app.services.modules.corpus_import_jobs import create_import_job, get_import_job, run_import_job
from app.services.modules.corpus_import_service import CorpusImportService
from app.services.modules.corpus_search_service import CorpusSearchService
from app.services.shared.structure_chunker import DEFAULT_MAX_CHUNK, DEFAULT_MIN_CHUNK, DEFAULT_OVERLAP

router = APIRouter(prefix="/documents/corpora", tags=["documents-corpora"])


def _import_service(db: Session = Depends(get_db)) -> CorpusImportService:
    return CorpusImportService(db)


def _search_service(db: Session = Depends(get_db)) -> CorpusSearchService:
    return CorpusSearchService(db)


@router.get("", response_model=list[schemas.DocumentCorpusRead], summary="列出业务知识库")
def list_corpora(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-list", name="资料库列表")),
) -> list[schemas.DocumentCorpusRead]:
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
    response_model=Union[schemas.CorpusImportResult, schemas.CorpusImportJobAccepted],
    summary="导入到业务知识库",
)
async def import_corpus(
    background_tasks: BackgroundTasks,
    corpus_name: str = Form(..., description="资料名（相同则入同一物理表）"),
    file: UploadFile | None = File(
        default=None,
        description="单文件 .md/.txt 或 .zip（与 folder_path 三选一）",
    ),
    folder_path: str | None = Form(default=None, description="本机文件夹绝对路径"),
    replace_existing: bool = Form(True, description="覆盖同文件名已有切块"),
    chunk_strategy: str = Form("structure", description="structure | legacy"),
    max_chunk_len: int = Form(DEFAULT_MAX_CHUNK, ge=50, le=2000),
    min_chunk_len: int = Form(DEFAULT_MIN_CHUNK, ge=20, le=1000),
    chunk_overlap: int = Form(DEFAULT_OVERLAP, ge=0, le=500),
    async_mode: bool = Form(False, description="True 时立即返回 job_id，后台导入"),
    service: CorpusImportService = Depends(_import_service),
    _: User = Depends(require_permission("82.corpora-import", name="资料库导入")),
) -> Union[schemas.CorpusImportResult, schemas.CorpusImportJobAccepted]:
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

    params = {
        "corpus_name": corpus_name,
        "file_name": file_name,
        "file_text": file_text,
        "file_bytes": file_bytes,
        "folder_path": folder_path,
        "replace_existing": replace_existing,
        "chunk_strategy": chunk_strategy,
        "min_chunk_len": min_chunk_len,
        "max_chunk_len": max_chunk_len,
        "chunk_overlap": chunk_overlap,
    }
    if async_mode:
        job_id = create_import_job(corpus_name=corpus_name.strip())
        background_tasks.add_task(run_import_job, job_id, params)
        return schemas.CorpusImportJobAccepted(job_id=job_id)

    return service.import_upload_or_folder(**params)


@router.get("/files", response_model=schemas.CorpusFileListResult, summary="资料库内文件名列表")
def list_corpus_files(
    corpus_name: str = Query(..., description="资料名"),
    service: CorpusSearchService = Depends(_search_service),
    _: User = Depends(require_permission("82.corpora-files", name="资料库文件列表")),
) -> schemas.CorpusFileListResult:
    return service.list_files(corpus_name)


@router.delete("", response_model=schemas.CorpusClearResult, summary="清空资料库切块数据")
def clear_corpus(
    corpus_name: str = Query(..., description="资料名"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.corpora-clear", name="资料库清空")),
) -> schemas.CorpusClearResult:
    """只删切块数据，保留 document_corpora 注册与物理表结构。"""
    corpus = corpus_crud.get_corpus_by_name(db, corpus_name)
    if corpus is None:
        raise HTTPException(status_code=404, detail=f"资料库不存在: {corpus_name}")
    deleted = corpus_crud.clear_all_chunks(db, corpus.table_name)
    return schemas.CorpusClearResult(
        corpus_name=corpus.name,
        table_name=corpus.table_name,
        deleted_chunks=deleted,
    )


@router.get(
    "/search",
    response_model=list[schemas.DocumentChunkSearchResult],
    summary="业务知识库检索（vector / hybrid）",
)
def search_corpus(
    corpus_name: str = Query(..., description="资料名"),
    q: str | None = Query(default=None, description="查询文本"),
    limit: int = Query(default=5, ge=1, le=50),
    min_similarity: float = Query(default=0.55, ge=0.0, le=1.0),
    source_file: str | None = Query(default=None, description="可选：限定文件"),
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
    )


@router.get(
    "/search_and_llm",
    response_model=schemas.DocumentSearchPolishedResult,
    summary="业务知识库检索 + LLM 润色",
)
def search_corpus_and_llm(
    corpus_name: str = Query(..., description="资料名"),
    q: str | None = Query(default=None, description="查询文本"),
    limit: int = Query(default=5, ge=1, le=50),
    min_similarity: float = Query(default=0.55, ge=0.0, le=1.0),
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
    )
