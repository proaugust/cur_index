from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services.complaint_service import ComplaintService
from app.services.document_import_service import DocumentImportService
from app.services.document_search_service import DocumentSearchService


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_document_import_service(
    db: Session = Depends(get_db),
) -> DocumentImportService:
    return DocumentImportService(db)


def get_complaint_service(
    db: Session = Depends(get_db),
) -> ComplaintService:
    return ComplaintService(db)


def get_document_search_service(
    db: Session = Depends(get_db),
) -> DocumentSearchService:
    return DocumentSearchService(db)
