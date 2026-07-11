from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "sessions"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pack_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    pack_title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    current_topic_id: Mapped[str] = mapped_column(String(128), nullable=False)
    current_phase: Mapped[str] = mapped_column(String(16), nullable=False)
    current_step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    manifest: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    attempts: Mapped[list[Attempt]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    phase_progress_rows: Mapped[list[PhaseProgress]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    course_assess: Mapped[CourseAssessSession | None] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Attempt(Base):
    __tablename__ = "attempts"
    __table_args__ = {"schema": "sessions"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    topic_id: Mapped[str] = mapped_column(String(128), nullable=False)
    phase: Mapped[str] = mapped_column(String(16), nullable=False)
    step_id: Mapped[str] = mapped_column(String(128), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    submission: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    session: Mapped[Session] = relationship(back_populates="attempts")


class PhaseProgress(Base):
    __tablename__ = "phase_progress"
    __table_args__ = {"schema": "sessions"}

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    topic_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    study_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    study_skipped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    practice_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assess_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    assess_best_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    session: Mapped[Session] = relationship(back_populates="phase_progress_rows")


class CourseAssessSession(Base):
    __tablename__ = "course_assess_sessions"
    __table_args__ = {"schema": "sessions"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    session: Mapped[Session] = relationship(back_populates="course_assess")
