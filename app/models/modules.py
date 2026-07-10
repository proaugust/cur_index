from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_file: Mapped[str] = mapped_column(String(500), index=True)
    section_title: Mapped[str] = mapped_column(String(200), default="")
    section_path: Mapped[str] = mapped_column(String(200), default="")
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(512), nullable=True)


class ComplaintCategory(Base):
    __tablename__ = "complaint_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    seed_phrases: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim), nullable=True)

    complaints: Mapped[list["Complaint"]] = relationship(back_populates="category")


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(primary_key=True)
    complaint_text: Mapped[str] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    complaint_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embedding_dim), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("complaint_categories.id"), nullable=True, index=True)
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)

    category: Mapped["ComplaintCategory | None"] = relationship(back_populates="complaints")


class AttendancePerson(Base):
    __tablename__ = "attendance_persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    face_descriptor: Mapped[str] = mapped_column(Text)
    reference_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    punches: Mapped[list["AttendancePunch"]] = relationship(back_populates="person")


class AttendancePunch(Base):
    __tablename__ = "attendance_punches"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("attendance_persons.id"), index=True)
    punched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    person: Mapped["AttendancePerson"] = relationship(back_populates="punches")


class AiNewsLink(Base):
    __tablename__ = "ai_news_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(64), nullable=True)
    url: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    region: Mapped[str] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[str] = mapped_column(String(500), default="")
    letter: Mapped[str] = mapped_column(String(8), default="")
    color: Mapped[str] = mapped_column(String(16), default="#409EFF")
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP"))

    user: Mapped["User | None"] = relationship()
