from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.smart_route_service import route_question

router = APIRouter(prefix="/smart-route", tags=["smart-route"])


@router.post("/dispatch", response_model=schemas.SmartRouteResponse)
def dispatch_smart_route(
    body: schemas.SmartRouteRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("86.dispatch")),
) -> schemas.SmartRouteResponse:
    intent, message, employees = route_question(body.question, db)
    return schemas.SmartRouteResponse(
        question=body.question.strip(),
        intent=intent,
        message=message,
        employees=employees,
    )