"""Insight 深夜批处理后台启动（独立线程 + 独立 DB session，避免 HF HTTP 超时）。"""

from __future__ import annotations

import logging
import threading
from datetime import date
from typing import Literal

from fastapi import HTTPException, status

from app.database import SessionLocal
from app.schemas.insight import InsightNightlyJobAccepted
from app.services.modules.insight.nightly_job_service import InsightNightlyJobService

logger = logging.getLogger(__name__)

InsightRunMode = Literal["incremental", "full"]

_job_lock = threading.Lock()


def start_nightly_async(
    snapshot_date: date | None = None,
    *,
    with_prev_day: bool = False,
    mode: InsightRunMode = "incremental",
) -> InsightNightlyJobAccepted:
    if not _job_lock.acquire(blocking=False):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已有 Insight 批处理在运行，请稍后再试")

    db = SessionLocal()
    try:
        service = InsightNightlyJobService(db)
        accepted = service.prepare_async(
            snapshot_date=snapshot_date, with_prev_day=with_prev_day, mode=mode
        )
    except Exception:
        _job_lock.release()
        raise
    finally:
        db.close()

    target_date = accepted.snapshot_date
    log_id = accepted.analysis_log_id

    def _worker() -> None:
        worker_db = SessionLocal()
        try:
            InsightNightlyJobService(worker_db).run_nightly(
                snapshot_date=target_date,
                with_prev_day=with_prev_day,
                mode=mode,
                existing_log_id=log_id,
            )
        except BaseException:
            logger.exception("后台批处理异常 log_id=%s", log_id)
        finally:
            worker_db.close()
            _job_lock.release()

    threading.Thread(target=_worker, name=f"insight-nightly-{log_id}", daemon=True).start()
    return accepted
