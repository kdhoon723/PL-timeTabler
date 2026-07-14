from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from timetabler.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    grade: Mapped[int | None] = mapped_column(Integer)
    department: Mapped[str | None] = mapped_column(String(200))
    admission_year: Mapped[int | None] = mapped_column(Integer)
    entry_type: Mapped[str | None] = mapped_column(String(24))
    student_type: Mapped[str | None] = mapped_column(String(24))
    section_group: Mapped[str | None] = mapped_column(String(24))
    major_path: Mapped[str | None] = mapped_column(String(32))
    profile_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class PrivacyConsent(Base):
    __tablename__ = "privacy_consents"
    __table_args__ = (Index("ix_privacy_consents_user_agreed", "user_id", "agreed_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_version: Mapped[str] = mapped_column(String(40), nullable=False)
    agreed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    agreed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SavedTimetable(Base):
    __tablename__ = "saved_timetables"
    __table_args__ = (
        Index("ix_saved_timetables_user_semester", "user_id", "semester"),
        Index("ix_saved_timetables_user_favorite", "user_id", "favorite"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    semester: Mapped[str] = mapped_column(String(20), nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String(80))
    items_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    preferences_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class TimetableShare(Base):
    __tablename__ = "timetable_shares"
    __table_args__ = (Index("ix_timetable_shares_timetable", "timetable_id"),)

    share_code: Mapped[str] = mapped_column(String(32), primary_key=True)
    timetable_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("saved_timetables.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class CourseReview(Base):
    __tablename__ = "course_reviews"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "course_code",
            "professor",
            "semester",
            name="uq_course_reviews_author_course_offering",
        ),
        Index("ix_course_reviews_course_professor", "course_code", "professor"),
        Index("ix_course_reviews_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_code: Mapped[str] = mapped_column(String(40), nullable=False)
    course_name: Mapped[str] = mapped_column(String(240), nullable=False)
    professor: Mapped[str | None] = mapped_column(String(120))
    semester: Mapped[str] = mapped_column(String(20), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class CompletedCourse(Base):
    __tablename__ = "completed_courses"
    __table_args__ = (
        Index("ix_completed_courses_user_status", "user_id", "status"),
        Index("ix_completed_courses_user_semester", "user_id", "semester"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_code: Mapped[str | None] = mapped_column(String(40))
    course_name: Mapped[str] = mapped_column(String(240), nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(160), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120))
    semester: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class OptimizationJob(Base):
    __tablename__ = "optimization_jobs"
    __table_args__ = (Index("ix_optimization_jobs_claim", "status", "leased_until", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, index=True)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lease_token: Mapped[str | None] = mapped_column(String(36), unique=True)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class AuthOtpChallenge(Base):
    __tablename__ = "auth_otp_challenges"
    __table_args__ = (
        Index("ix_auth_otp_challenges_student_created", "student_number", "created_at"),
        Index("ix_auth_otp_challenges_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_number: Mapped[str] = mapped_column(String(20), nullable=False)
    code_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_student", "student_number"),
        Index("ix_auth_sessions_token_digest", "token_digest", unique=True),
        Index("ix_auth_sessions_expires", "expires_at"),
        Index("ix_auth_sessions_revoked", "revoked_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_number: Mapped[str] = mapped_column(String(20), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )


class AuthRateEvent(Base):
    __tablename__ = "auth_rate_events"
    __table_args__ = (
        Index("ix_auth_rate_events_account", "kind", "account_digest", "created_at"),
        Index("ix_auth_rate_events_ip", "kind", "ip_digest", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    account_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    ip_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
