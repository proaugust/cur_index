"""RAG 场景演示 API：NL2SQL / 长文档 / Web 时效。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.modules.rag_longdoc_service import RagLongdocService
from app.services.modules.rag_nl2sql_service import RagNl2sqlService
from app.services.modules.rag_web_search_service import RagWebSearchService

router = APIRouter(prefix="/rag-demos", tags=["rag-demos"])


@router.post("/nl2sql", response_model=schemas.RagNl2sqlResult, summary="NL2SQL 演示（只读）")
def rag_nl2sql(
    body: schemas.RagNl2sqlRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.nl2sql", name="NL2SQL演示")),
) -> schemas.RagNl2sqlResult:
    result = RagNl2sqlService(db).run(body.question, row_limit=body.row_limit)
    return schemas.RagNl2sqlResult(**result)


@router.post("/longdoc", response_model=schemas.RagLongdocResult, summary="长文档摘要增强问答")
def rag_longdoc(
    body: schemas.RagLongdocRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("82.longdoc", name="长文档审计演示")),
) -> schemas.RagLongdocResult:
    result = RagLongdocService(db).analyze(body.corpus_name, body.question, limit=body.limit)
    return schemas.RagLongdocResult(**result)


@router.post("/web-search", response_model=schemas.RagWebSearchResult, summary="时效 Web-Search RAG")
def rag_web_search(
    body: schemas.RagWebSearchRequest,
    _: User = Depends(require_permission("82.web-search", name="Web时效检索")),
) -> schemas.RagWebSearchResult:
    result = RagWebSearchService().search_and_answer(body.question, count=body.count)
    return schemas.RagWebSearchResult(**result)
