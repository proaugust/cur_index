from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import schemas
from app.core.deps import get_db
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["attendance"])


@router.post("/punch", response_model=schemas.AttendancePunchResponse)
def punch_attendance(body: schemas.AttendancePunchRequest, db: Session = Depends(get_db)) -> schemas.AttendancePunchResponse:
    return attendance_service.punch(db, body)


@router.get("/punches", response_model=schemas.AttendancePunchesPage)
def list_attendance_punches(
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> schemas.AttendancePunchesPage:
    return attendance_service.list_punches(db, user_id=user_id, page=page, page_size=page_size)


@router.get("/persons", response_model=list[schemas.AttendancePersonRead])
def list_attendance_persons(
    user_id: str | None = Query(default=None, description="按用户 ID 筛选"),
    db: Session = Depends(get_db),
) -> list[schemas.AttendancePersonRead]:
    return attendance_service.list_persons(db, user_id=user_id)


@router.get("/persons/{user_id}/photo")
def get_attendance_person_photo(user_id: str, db: Session = Depends(get_db)) -> FileResponse:
    path = attendance_service.get_person_photo_path(db, user_id)
    return FileResponse(path, media_type="image/jpeg", filename=path.name)


@router.delete("/punches/{punch_id}")
def delete_attendance_punch(punch_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    attendance_service.delete_punch(db, punch_id)
    return {"message": "deleted"}


@router.delete("/persons/{person_id}")
def delete_attendance_person(person_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    attendance_service.delete_person(db, person_id)
    return {"message": "deleted"}
