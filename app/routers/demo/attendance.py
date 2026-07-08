from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.core.permissions import require_permission
from app.models import User
from app.services.demo import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])

_NO_STORE_HEADERS = {"Cache-Control": "no-store"}


@router.post("/punch", response_model=schemas.AttendancePunchResponse)
def punch_attendance(
    body: schemas.AttendancePunchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("87.punch", name="人脸打卡")),
) -> schemas.AttendancePunchResponse:
    return attendance_service.punch(db, body)


@router.get("/punches", response_model=schemas.AttendancePunchesPage)
def list_attendance_punches(
    response: Response,
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("87.punches", name="打卡历史")),
) -> schemas.AttendancePunchesPage:
    response.headers.update(_NO_STORE_HEADERS)
    return attendance_service.list_punches(db, user_id=user_id, page=page, page_size=page_size)


@router.get("/persons", response_model=list[schemas.AttendancePersonRead])
def list_attendance_persons(
    response: Response,
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("87.persons", name="已登记人员")),
) -> list[schemas.AttendancePersonRead]:
    response.headers.update(_NO_STORE_HEADERS)
    return attendance_service.list_persons(db, user_id=user_id)


@router.get("/persons/{user_id}/photo")
def get_attendance_person_photo(
    user_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("87.person-photo", name="人员照片")),
) -> FileResponse:
    path = attendance_service.get_person_photo_path(db, user_id)
    return FileResponse(path, media_type="image/jpeg", filename=path.name)


@router.delete("/punches/{punch_id}")
def delete_attendance_punch(
    punch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("87.punch-delete", name="删除打卡")),
) -> dict[str, str]:
    attendance_service.delete_punch(db, punch_id)
    return {"message": "deleted"}


@router.delete("/persons/{person_id}")
def delete_attendance_person(
    person_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("87.person-delete", name="删除人员")),
) -> dict[str, str]:
    attendance_service.delete_person(db, person_id)
    return {"message": "deleted"}
