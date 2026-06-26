import base64
import json
import math
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, inspect, text
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.config import settings

def _euclidean_distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _parse_descriptor(raw: str) -> list[float]:
    return json.loads(raw)


def _next_user_id(db: Session) -> str:
    max_id = db.query(func.max(models.AttendancePerson.id)).scalar() or 0
    return f"U{max_id + 1:04d}"


def _blend_descriptors(stored: list[float], incoming: list[float], new_weight: float = 0.7) -> list[float]:
    old_weight = 1 - new_weight
    return [old * old_weight + inc * new_weight for old, inc in zip(stored, incoming)]


def _find_matching_person(
    db: Session, descriptor: list[float], threshold: float
) -> tuple[models.AttendancePerson | None, float | None]:
    best_person: models.AttendancePerson | None = None
    best_distance: float | None = None

    for person in db.query(models.AttendancePerson).all():
        stored = _parse_descriptor(person.face_descriptor)
        distance = _euclidean_distance(descriptor, stored)
        if distance <= threshold and (best_distance is None or distance < best_distance):
            best_person = person
            best_distance = distance

    return best_person, best_distance


def _get_last_punch(db: Session, person_id: int) -> models.AttendancePunch | None:
    return (
        db.query(models.AttendancePunch)
        .filter(models.AttendancePunch.person_id == person_id)
        .order_by(models.AttendancePunch.punched_at.desc())
        .first()
    )


def _ensure_person_columns(bind) -> None:
    inspector = inspect(bind)
    if "attendance_persons" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("attendance_persons")}
    statements: list[str] = []
    if "reference_image" not in columns:
        statements.append("ALTER TABLE attendance_persons ADD COLUMN reference_image VARCHAR(500)")
    if "reference_score" not in columns:
        statements.append("ALTER TABLE attendance_persons ADD COLUMN reference_score DOUBLE PRECISION")
    if not statements:
        return
    with bind.connect() as conn:
        for statement in statements:
            conn.execute(text(statement))
        conn.commit()


def ensure_attendance_tables(db: Session) -> None:
    bind = db.get_bind()
    models.AttendancePerson.__table__.create(bind=bind, checkfirst=True)
    models.AttendancePunch.__table__.create(bind=bind, checkfirst=True)
    _ensure_person_columns(bind)
    settings.attendance_faces_dir.mkdir(parents=True, exist_ok=True)


def _face_image_path(user_id: str) -> Path:
    return settings.attendance_faces_dir / f"{user_id}.jpg"


def _decode_face_image(face_image: str) -> bytes:
    payload = face_image.strip()
    if "," in payload:
        payload = payload.split(",", 1)[1]
    try:
        return base64.b64decode(payload, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="人脸图片格式无效") from exc


def _save_reference_image(user_id: str, face_image: str) -> str:
    image_bytes = _decode_face_image(face_image)
    if len(image_bytes) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="人脸图片过大")
    filename = f"{user_id}.jpg"
    path = settings.attendance_faces_dir / filename
    path.write_bytes(image_bytes)
    return filename


def _delete_reference_image_file(reference_image: str | None) -> None:
    if not reference_image:
        return
    path = settings.attendance_faces_dir / reference_image
    if path.is_file():
        path.unlink()


def _maybe_update_reference_image(
    person: models.AttendancePerson,
    *,
    face_image: str | None,
    face_score: float | None,
    force: bool = False,
) -> bool:
    if not face_image:
        return False

    score = face_score if face_score is not None else 0.0
    should_update = force or person.reference_image is None
    if not should_update and person.reference_score is not None:
        should_update = score > person.reference_score
    if not should_update and person.reference_score is None:
        should_update = True
    if not should_update:
        return False

    filename = _save_reference_image(person.user_id, face_image)
    person.reference_image = filename
    person.reference_score = score
    return True


def punch(db: Session, body: schemas.AttendancePunchRequest) -> schemas.AttendancePunchResponse:
    ensure_attendance_tables(db)
    descriptor = body.descriptor
    threshold = body.match_threshold
    now = datetime.utcnow()

    person, match_distance = _find_matching_person(db, descriptor, threshold)
    is_new_person = person is None

    punch_skipped = False
    last_punch = None

    if is_new_person:
        person = models.AttendancePerson(
            user_id=_next_user_id(db),
            face_descriptor=json.dumps(descriptor),
            created_at=now,
            updated_at=now,
        )
        db.add(person)
        db.flush()
    else:
        last_punch = _get_last_punch(db, person.id)
        if (
            body.dedup_enabled
            and last_punch
            and (now - last_punch.punched_at).total_seconds() < body.dedup_seconds
        ):
            punch_skipped = True

        stored = _parse_descriptor(person.face_descriptor)
        person.face_descriptor = json.dumps(_blend_descriptors(stored, descriptor))
        person.updated_at = now

    reference_image_updated = _maybe_update_reference_image(
        person,
        face_image=body.face_image,
        face_score=body.face_score,
        force=is_new_person,
    )

    if punch_skipped and last_punch:
        db.commit()
        db.refresh(person)
        return schemas.AttendancePunchResponse(
            user_id=person.user_id,
            punched_at=last_punch.punched_at,
            is_new_person=False,
            match_distance=match_distance,
            reference_image_updated=reference_image_updated,
            punch_skipped=True,
        )

    punch_row = models.AttendancePunch(person_id=person.id, punched_at=now)
    db.add(punch_row)
    db.commit()
    db.refresh(person)
    db.refresh(punch_row)

    return schemas.AttendancePunchResponse(
        user_id=person.user_id,
        punched_at=punch_row.punched_at,
        is_new_person=is_new_person,
        match_distance=match_distance,
        reference_image_updated=reference_image_updated,
        punch_skipped=False,
    )


def list_punches(
    db: Session,
    *,
    user_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> schemas.AttendancePunchesPage:
    ensure_attendance_tables(db)
    query = db.query(models.AttendancePunch, models.AttendancePerson.user_id).join(
        models.AttendancePerson, models.AttendancePunch.person_id == models.AttendancePerson.id
    )
    if user_id:
        keyword = user_id.strip()
        query = query.filter(models.AttendancePerson.user_id.ilike(f"%{keyword}%"))

    total = query.count()
    rows = (
        query.order_by(models.AttendancePunch.punched_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = [
        schemas.AttendancePunchRead(id=punch.id, user_id=uid, punched_at=punch.punched_at) for punch, uid in rows
    ]
    return schemas.AttendancePunchesPage(items=items, total=total, page=page, page_size=page_size)


def list_persons(db: Session, user_id: str | None = None) -> list[schemas.AttendancePersonRead]:
    ensure_attendance_tables(db)
    query = db.query(models.AttendancePerson)
    if user_id:
        keyword = user_id.strip()
        query = query.filter(models.AttendancePerson.user_id.ilike(f"%{keyword}%"))
    rows = query.order_by(models.AttendancePerson.id).all()
    count_rows = (
        db.query(models.AttendancePunch.person_id, func.count(models.AttendancePunch.id))
        .group_by(models.AttendancePunch.person_id)
        .all()
    )
    punch_counts = {person_id: count for person_id, count in count_rows}
    return [
        schemas.AttendancePersonRead(
            id=person.id,
            user_id=person.user_id,
            created_at=person.created_at,
            punch_count=punch_counts.get(person.id, 0),
            has_reference_image=bool(person.reference_image),
        )
        for person in rows
    ]


def get_person_photo_path(db: Session, user_id: str) -> Path:
    ensure_attendance_tables(db)
    person = db.query(models.AttendancePerson).filter(models.AttendancePerson.user_id == user_id).first()
    if not person or not person.reference_image:
        raise HTTPException(status_code=404, detail="标准照不存在")
    path = settings.attendance_faces_dir / person.reference_image
    if not path.is_file():
        raise HTTPException(status_code=404, detail="标准照文件不存在")
    return path


def delete_punch(db: Session, punch_id: int) -> None:
    ensure_attendance_tables(db)
    punch_row = db.query(models.AttendancePunch).filter(models.AttendancePunch.id == punch_id).first()
    if not punch_row:
        raise HTTPException(status_code=404, detail="打卡记录不存在")
    db.delete(punch_row)
    db.commit()


def delete_person(db: Session, person_id: int) -> None:
    ensure_attendance_tables(db)
    person = db.query(models.AttendancePerson).filter(models.AttendancePerson.id == person_id).first()
    if not person:
        raise HTTPException(status_code=404, detail="人员不存在")
    reference_image = person.reference_image
    db.query(models.AttendancePunch).filter(models.AttendancePunch.person_id == person_id).delete(synchronize_session=False)
    db.delete(person)
    db.commit()
    _delete_reference_image_file(reference_image)
