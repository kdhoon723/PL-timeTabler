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
    LargeBinary,
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


class HistoricalArchiveManifest(Base):
    __tablename__ = "historical_archive_manifests"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_archive: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HistoricalTermDataset(Base):
    __tablename__ = "historical_term_datasets"
    __table_args__ = (
        UniqueConstraint("academic_year", "term_code", name="uq_historical_term_year_code"),
        Index("ix_historical_term_year_code", "academic_year", "term_code"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    term_code: Mapped[str] = mapped_column(String(8), nullable=False)
    term_name: Mapped[str] = mapped_column(String(80), nullable=False)
    data_status: Mapped[str] = mapped_column(String(24), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_archive: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HistoricalCourseOffering(Base):
    __tablename__ = "historical_course_offerings"
    __table_args__ = (
        UniqueConstraint(
            "academic_year",
            "term_code",
            "course_code",
            "section_code",
            name="uq_historical_offering_identity",
        ),
        Index("ix_historical_offering_term", "academic_year", "term_code"),
        Index("ix_historical_offering_course", "course_code"),
        Index("ix_historical_offering_name", "korean_name"),
        Index("ix_historical_offering_category", "completion_category"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("historical_term_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    term_code: Mapped[str] = mapped_column(String(8), nullable=False)
    course_code: Mapped[str] = mapped_column(String(40), nullable=False)
    section_code: Mapped[str] = mapped_column(String(40), nullable=False)
    korean_name: Mapped[str] = mapped_column(String(240), nullable=False)
    english_name: Mapped[str | None] = mapped_column(String(400))
    professor_name: Mapped[str | None] = mapped_column(String(240))
    completion_category: Mapped[str | None] = mapped_column(String(160))
    credits: Mapped[float | None] = mapped_column(Float)
    lecture_hours: Mapped[float | None] = mapped_column(Float)
    practice_hours: Mapped[float | None] = mapped_column(Float)
    raw_lecture_time: Mapped[str | None] = mapped_column(Text)
    raw_location: Mapped[str | None] = mapped_column(Text)
    target_grade: Mapped[str | None] = mapped_column(String(120))
    listing_status: Mapped[str | None] = mapped_column(String(40))
    detail_status: Mapped[str | None] = mapped_column(String(40))
    category_contexts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    department_contexts: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    department_search_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class HistoricalCurriculumDataset(Base):
    __tablename__ = "historical_curriculum_datasets"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    department_count: Mapped[int] = mapped_column(Integer, nullable=False)
    course_record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_archive: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HistoricalCurriculumDepartment(Base):
    __tablename__ = "historical_curriculum_departments"
    __table_args__ = (
        UniqueConstraint(
            "academic_year", "department_code", name="uq_historical_curriculum_department"
        ),
        Index("ix_historical_curriculum_department_name", "department_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("historical_curriculum_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    college_code: Mapped[str | None] = mapped_column(String(40))
    college_name: Mapped[str | None] = mapped_column(String(240))
    department_code: Mapped[str] = mapped_column(String(40), nullable=False)
    department_name: Mapped[str] = mapped_column(String(240), nullable=False)
    course_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class HistoricalRelationDataset(Base):
    __tablename__ = "historical_relation_datasets"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    replacement_count: Mapped[int] = mapped_column(Integer, nullable=False)
    equivalent_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    source_archive: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class HistoricalCourseRelation(Base):
    __tablename__ = "historical_course_relations"
    __table_args__ = (
        Index("ix_historical_relation_type_year", "relation_type", "designated_year"),
        Index("ix_historical_relation_original_name", "original_course_name"),
        Index("ix_historical_relation_related_name", "related_course_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("historical_relation_datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(24), nullable=False)
    designated_year: Mapped[str | None] = mapped_column(String(20))
    designated_term: Mapped[str | None] = mapped_column(String(20))
    original_course_name: Mapped[str] = mapped_column(String(240), nullable=False)
    original_category: Mapped[str | None] = mapped_column(String(160))
    original_credits: Mapped[float | None] = mapped_column(Float)
    original_college: Mapped[str | None] = mapped_column(String(240))
    original_department: Mapped[str | None] = mapped_column(String(240))
    related_course_name: Mapped[str] = mapped_column(String(240), nullable=False)
    related_category: Mapped[str | None] = mapped_column(String(160))
    related_credits: Mapped[float | None] = mapped_column(Float)
    related_department: Mapped[str | None] = mapped_column(String(240))
    note: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


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
    historical_offering_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("historical_course_offerings.id", ondelete="SET NULL"),
        index=True,
    )
    course_code: Mapped[str | None] = mapped_column(String(40))
    section_code: Mapped[str | None] = mapped_column(String(40))
    course_name: Mapped[str] = mapped_column(String(240), nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str] = mapped_column(String(160), nullable=False)
    area: Mapped[str | None] = mapped_column(String(120))
    semester: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    input_source: Mapped[str] = mapped_column(String(32), nullable=False, default="MANUAL")
    source_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
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
