"""业务知识库异步导入：进程内 job 状态（重启即丢）。"""

from __future__ import annotations

import threading
import uuid
from typing import Any

from fastapi import HTTPException

from app.database import SessionLocal
from app.services.modules.corpus_import_service import CorpusImportService
from app.services.ops.error_log_service import record_app_error

_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def create_import_job(*, corpus_name: str, files_total: int = 0) -> str:
    job_id = uuid.uuid4().hex
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "corpus_name": corpus_name,
            "files_done": 0,
            "files_total": files_total,
            "chunks": 0,
            "error": None,
            "result": None,
        }
    return job_id


def get_import_job(job_id: str) -> dict[str, Any] | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def _update_job(job_id: str, **fields: Any) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return
        job.update(fields)


def run_import_job(job_id: str, params: dict[str, Any]) -> None:
    _update_job(job_id, status="running")
    db = SessionLocal()
    try:

        def on_progress(done: int, total: int) -> None:
            _update_job(job_id, files_done=done, files_total=total)

        service = CorpusImportService(db)
        result = service.import_upload_or_folder(on_progress=on_progress, **params)
        _update_job(
            job_id,
            status="done",
            files_done=result.files,
            files_total=result.files,
            chunks=result.chunks,
            result=result.model_dump(),
            error=None,
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        _update_job(job_id, status="failed", error=detail)
        record_app_error(
            source="corpus_import",
            message=detail[:500],
            error_type="HTTPException",
            ref_type="import_job",
            ref_id=job_id,
            path="/documents/corpora/import",
            method="POST",
        )
    except Exception as exc:
        _update_job(job_id, status="failed", error=str(exc))
        record_app_error(
            source="corpus_import",
            message=f"导入任务失败: {exc}"[:500],
            exc=exc,
            ref_type="import_job",
            ref_id=job_id,
            path="/documents/corpora/import",
            method="POST",
        )
    finally:
        db.close()
