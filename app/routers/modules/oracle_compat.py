from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.modules.oracle_compat_demo import (
    BENCH_DEFAULT,
    BENCH_MAX,
    BENCH_MIN,
    clear_data,
    extension_status,
    list_rows,
    run_cases,
    run_one_case,
    run_one_sql,
    seed_data,
)

router = APIRouter(prefix="/oracle_compat", tags=["oracle_compat"])


class SeedBody(BaseModel):
    rows: int = Field(default=BENCH_DEFAULT, ge=BENCH_MIN, le=BENCH_MAX)


class RunCaseBody(BaseModel):
    case_id: str = Field(min_length=1, max_length=64)
    sample_sql: str = Field(min_length=1)
    check_sql: str = Field(min_length=1)
    plugin_bench: str = Field(min_length=1)
    native_bench: str = Field(min_length=1)


class RunSqlBody(BaseModel):
    case_id: str = Field(min_length=1, max_length=64)
    kind: str = Field(pattern="^(sample_sql|check_sql|plugin_bench|native_bench)$")
    sql: str = Field(min_length=1)


def _fail(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/status")
def oracle_status(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("93.run", name="Oracle 兼容测试")),
) -> dict:
    return extension_status(db)


@router.post("/seed")
def oracle_seed(
    body: SeedBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("93.run", name="Oracle 兼容测试")),
) -> dict:
    try:
        return seed_data(db, body.rows)
    except RuntimeError as exc:
        raise _fail(exc) from exc


@router.post("/clear")
def oracle_clear(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("93.run", name="Oracle 兼容测试")),
) -> dict:
    try:
        return clear_data(db)
    except RuntimeError as exc:
        raise _fail(exc) from exc


@router.get("/rows")
def oracle_rows(
    table: str = Query(default="emp_bench", pattern="^(emp|emp_bench|dept)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("93.run", name="Oracle 兼容测试")),
) -> dict:
    try:
        return list_rows(db, table=table, page=page, page_size=page_size)
    except RuntimeError as exc:
        raise _fail(exc) from exc


@router.post("/run")
def oracle_run(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("93.run", name="Oracle 兼容测试")),
) -> dict:
    try:
        return run_cases(db)
    except RuntimeError as exc:
        raise _fail(exc) from exc


@router.post("/run_case")
def oracle_run_case(
    body: RunCaseBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("93.run", name="Oracle 兼容测试")),
) -> dict:
    try:
        return run_one_case(
            db,
            case_id=body.case_id,
            sample_sql=body.sample_sql,
            check_sql=body.check_sql,
            plugin_bench=body.plugin_bench,
            native_bench=body.native_bench,
        )
    except RuntimeError as exc:
        raise _fail(exc) from exc


@router.post("/run_sql")
def oracle_run_sql(
    body: RunSqlBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("93.run", name="Oracle 兼容测试")),
) -> dict:
    try:
        return run_one_sql(db, case_id=body.case_id, kind=body.kind, sql=body.sql)
    except RuntimeError as exc:
        raise _fail(exc) from exc
