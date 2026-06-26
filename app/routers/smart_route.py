from fastapi import APIRouter

from app import schemas
from app.services.smart_route_service import route_question

router = APIRouter(prefix="/smart-route", tags=["smart-route"])


@router.post("/dispatch", response_model=schemas.SmartRouteResponse)
def dispatch_smart_route(body: schemas.SmartRouteRequest) -> schemas.SmartRouteResponse:
    intent, message = route_question(body.question)
    return schemas.SmartRouteResponse(question=body.question.strip(), intent=intent, message=message)
