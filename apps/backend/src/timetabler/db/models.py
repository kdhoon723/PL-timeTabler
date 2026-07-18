from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
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


class RequirementDataset(Base):
    __tablename__ = "requirement_datasets"
    __table_args__ = (
        CheckConstraint("record_count >= 0", name="ck_requirement_datasets_record_count"),
        CheckConstraint(
            "admission_year IS NULL OR admission_year BETWEEN 1900 AND 2100",
            name="ck_requirement_datasets_admission_year",
        ),
        CheckConstraint(
            "effective_year IS NULL OR effective_year BETWEEN 1900 AND 2100",
            name="ck_requirement_datasets_effective_year",
        ),
        Index("ix_requirement_datasets_kind_year", "kind", "admission_year", "effective_year"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    admission_year: Mapped[int | None] = mapped_column(Integer)
    effective_year: Mapped[int | None] = mapped_column(Integer)
    as_of: Mapped[date | None] = mapped_column(Date)
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CurriculumProgramRequirement(Base):
    __tablename__ = "curriculum_program_requirements"
    __table_args__ = (
        CheckConstraint(
            "admission_year BETWEEN 1900 AND 2100",
            name="ck_curriculum_program_admission_year",
        ),
        CheckConstraint(
            "source_course_count >= 0 AND required_course_count >= 0",
            name="ck_curriculum_program_course_counts",
        ),
        UniqueConstraint(
            "dataset_id", "academic_unit_key", name="uq_curriculum_program_requirement"
        ),
        Index(
            "ix_curriculum_program_requirements_year_unit",
            "admission_year",
            "academic_unit_key",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("requirement_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_unit: Mapped[str] = mapped_column(String(240), nullable=False)
    academic_unit_key: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    source_locators: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    source_course_count: Mapped[int] = mapped_column(Integer, nullable=False)
    required_course_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class CurriculumProgramAlias(Base):
    __tablename__ = "curriculum_program_aliases"
    __table_args__ = (
        UniqueConstraint(
            "admission_year", "alias_key", "program_id", name="uq_curriculum_program_alias"
        ),
        Index("ix_curriculum_program_aliases_year_key", "admission_year", "alias_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    program_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("curriculum_program_requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    alias: Mapped[str] = mapped_column(String(240), nullable=False)
    alias_key: Mapped[str] = mapped_column(String(240), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False)


class CurriculumRequiredCourse(Base):
    __tablename__ = "curriculum_required_courses"
    __table_args__ = (
        CheckConstraint(
            "classification IN ('전기', '전필')",
            name="ck_curriculum_required_course_classification",
        ),
        CheckConstraint("credits IS NULL OR credits >= 0", name="ck_required_course_credits"),
        CheckConstraint(
            "grade IS NULL OR grade BETWEEN 1 AND 6",
            name="ck_required_course_grade",
        ),
        UniqueConstraint(
            "program_id",
            "classification",
            "course_code",
            name="uq_curriculum_required_course",
        ),
        Index("ix_curriculum_required_courses_program", "program_id", "classification"),
        Index("ix_curriculum_required_courses_code", "course_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    program_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("curriculum_program_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    classification: Mapped[str] = mapped_column(String(20), nullable=False)
    course_code: Mapped[str] = mapped_column(String(40), nullable=False)
    course_name: Mapped[str] = mapped_column(String(240), nullable=False)
    credits: Mapped[float | None] = mapped_column(Float)
    grade: Mapped[int | None] = mapped_column(Integer)
    semesters: Mapped[list[int]] = mapped_column(JSON, nullable=False)
    source_locator: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class GraduationRequirementRule(Base):
    __tablename__ = "graduation_requirement_rules"
    __table_args__ = (
        CheckConstraint(
            "admission_year_start IS NULL OR admission_year_end IS NULL "
            "OR admission_year_start <= admission_year_end",
            name="ck_graduation_rule_admission_year_range",
        ),
        Index(
            "ix_graduation_requirement_rules_lookup",
            "academic_unit_key",
            "admission_year_start",
            "admission_year_end",
            "effective_year",
        ),
        Index("ix_graduation_requirement_rules_dataset", "dataset_id", "rule_kind"),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("requirement_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    category_code: Mapped[str | None] = mapped_column(String(40))
    academic_unit: Mapped[str | None] = mapped_column(String(240))
    academic_unit_key: Mapped[str | None] = mapped_column(String(240))
    admission_year_start: Mapped[int | None] = mapped_column(Integer)
    admission_year_end: Mapped[int | None] = mapped_column(Integer)
    effective_year: Mapped[int | None] = mapped_column(Integer)
    student_type: Mapped[str | None] = mapped_column(String(40))
    program_path: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(Text)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class GraduationLiberalRequirementSet(Base):
    __tablename__ = "graduation_liberal_requirement_sets"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "signature",
            name="uq_graduation_liberal_requirement_set_signature",
        ),
        CheckConstraint(
            "admission_year BETWEEN 1900 AND 2100",
            name="ck_graduation_liberal_set_admission_year",
        ),
        CheckConstraint(
            "required_credits_min >= 0 AND elective_credits_min >= 0 "
            "AND total_credits_min >= 0 "
            "AND (total_credits_max IS NULL OR total_credits_max >= total_credits_min)",
            name="ck_graduation_liberal_set_credits",
        ),
        Index(
            "ix_graduation_liberal_sets_year_type",
            "admission_year",
            "student_type",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("requirement_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    signature: Mapped[str] = mapped_column(String(64), nullable=False)
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    student_type: Mapped[str] = mapped_column(String(40), nullable=False)
    required_credits_min: Mapped[int] = mapped_column(Integer, nullable=False)
    elective_credits_min: Mapped[int] = mapped_column(Integer, nullable=False)
    total_credits_min: Mapped[int] = mapped_column(Integer, nullable=False)
    total_credits_max: Mapped[int | None] = mapped_column(Integer)


class GraduationLiberalRequiredCourse(Base):
    __tablename__ = "graduation_liberal_required_courses"
    __table_args__ = (
        UniqueConstraint(
            "requirement_set_id",
            "position",
            name="uq_graduation_liberal_course_position",
        ),
        UniqueConstraint(
            "requirement_set_id",
            "course_code",
            name="uq_graduation_liberal_course_code",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_liberal_course_position"),
        CheckConstraint("credits > 0", name="ck_graduation_liberal_course_credits"),
        CheckConstraint(
            "grade IS NULL OR grade BETWEEN 1 AND 6",
            name="ck_graduation_liberal_course_grade",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    requirement_set_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_liberal_requirement_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    course_code: Mapped[str | None] = mapped_column(String(40))
    course_name: Mapped[str] = mapped_column(String(240), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[int | None] = mapped_column(Integer)
    source_page: Mapped[int] = mapped_column(Integer, nullable=False)


class GraduationLiberalCourseAlias(Base):
    __tablename__ = "graduation_liberal_course_aliases"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "alias_key",
            name="uq_graduation_liberal_course_alias",
        ),
        UniqueConstraint(
            "course_id",
            "position",
            name="uq_graduation_liberal_course_alias_position",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_liberal_course_alias_position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_liberal_required_courses.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    alias: Mapped[str] = mapped_column(String(240), nullable=False)
    alias_key: Mapped[str] = mapped_column(String(240), nullable=False)


class GraduationLiberalCourseTerm(Base):
    __tablename__ = "graduation_liberal_course_terms"
    __table_args__ = (
        CheckConstraint("semester IN (1, 2)", name="ck_graduation_liberal_course_term"),
    )

    course_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_liberal_required_courses.id", ondelete="CASCADE"),
        primary_key=True,
    )
    semester: Mapped[int] = mapped_column(Integer, primary_key=True)


class GraduationLiberalAreaRequirement(Base):
    __tablename__ = "graduation_liberal_area_requirements"
    __table_args__ = (
        UniqueConstraint(
            "requirement_set_id",
            "area",
            name="uq_graduation_liberal_area",
        ),
        UniqueConstraint(
            "requirement_set_id",
            "position",
            name="uq_graduation_liberal_area_position",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_liberal_area_position"),
        CheckConstraint("min_courses >= 0", name="ck_graduation_liberal_area_courses"),
        CheckConstraint(
            "min_credits IS NULL OR min_credits >= 0",
            name="ck_graduation_liberal_area_credits",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    requirement_set_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_liberal_requirement_sets.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    area: Mapped[str] = mapped_column(String(160), nullable=False)
    min_courses: Mapped[int] = mapped_column(Integer, nullable=False)
    min_credits: Mapped[int | None] = mapped_column(Integer)


class GraduationCreditProfile(Base):
    __tablename__ = "graduation_credit_profiles"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_rule_id",
            name="uq_graduation_credit_profile_source_rule",
        ),
        UniqueConstraint(
            "dataset_id",
            "academic_unit_key",
            "admission_year",
            "student_type",
            "program_path",
            name="uq_graduation_credit_profile_scope",
        ),
        CheckConstraint(
            "admission_year BETWEEN 1900 AND 2100",
            name="ck_graduation_credit_profile_admission_year",
        ),
        CheckConstraint(
            "program_path IN ('ADVANCED_MAJOR', 'DOUBLE_MAJOR', 'MINOR', 'MICRO_MAJOR')",
            name="ck_graduation_credit_profile_path",
        ),
        CheckConstraint(
            "total_credits_min >= 0 AND major_foundation_min >= 0 "
            "AND major_required_min >= 0 AND major_elective_min >= 0 "
            "AND (additional_major_min IS NULL OR additional_major_min >= 0) "
            "AND primary_major_min >= 0 "
            "AND (secondary_program_min IS NULL OR secondary_program_min >= 0)",
            name="ck_graduation_credit_profile_credits",
        ),
        Index(
            "ix_graduation_credit_profile_lookup",
            "academic_unit_key",
            "admission_year",
            "student_type",
            "program_path",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("requirement_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_rule_id: Mapped[str] = mapped_column(String(160), nullable=False)
    liberal_requirement_set_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_liberal_requirement_sets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    academic_unit: Mapped[str] = mapped_column(String(240), nullable=False)
    academic_unit_key: Mapped[str] = mapped_column(String(240), nullable=False)
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    student_type: Mapped[str] = mapped_column(String(40), nullable=False)
    program_path: Mapped[str] = mapped_column(String(40), nullable=False)
    total_credits_min: Mapped[int] = mapped_column(Integer, nullable=False)
    major_foundation_min: Mapped[int] = mapped_column(Integer, nullable=False)
    major_required_min: Mapped[int] = mapped_column(Integer, nullable=False)
    major_elective_min: Mapped[int] = mapped_column(Integer, nullable=False)
    additional_major_min: Mapped[int | None] = mapped_column(Integer)
    primary_major_min: Mapped[int] = mapped_column(Integer, nullable=False)
    secondary_program_min: Mapped[int | None] = mapped_column(Integer)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GraduationCreditProfileSourceReference(Base):
    __tablename__ = "graduation_credit_profile_source_refs"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "source_ref",
            name="uq_graduation_credit_profile_source_ref",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_credit_profile_source_ref_position"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_credit_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)


class GraduationCreditProfileAcademicUnitAlias(Base):
    __tablename__ = "graduation_credit_profile_academic_unit_aliases"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "alias_key",
            name="uq_graduation_credit_profile_academic_unit_alias",
        ),
        CheckConstraint(
            "position >= 0",
            name="ck_graduation_credit_profile_academic_unit_alias_position",
        ),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_credit_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    alias: Mapped[str] = mapped_column(String(240), nullable=False)
    alias_key: Mapped[str] = mapped_column(String(240), nullable=False)


class GraduationCreditProfileWarning(Base):
    __tablename__ = "graduation_credit_profile_warnings"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "code",
            name="uq_graduation_credit_profile_warning",
        ),
        UniqueConstraint(
            "profile_id",
            "position",
            name="uq_graduation_credit_profile_warning_position",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_credit_profile_warning_position"),
        CheckConstraint(
            "calculated >= 0 AND printed >= 0",
            name="ck_graduation_credit_profile_warning_values",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_credit_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    calculated: Mapped[int] = mapped_column(Integer, nullable=False)
    printed: Mapped[int] = mapped_column(Integer, nullable=False)


class GraduationAssessmentProfile(Base):
    __tablename__ = "graduation_assessment_profiles"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_rule_id",
            name="uq_graduation_assessment_profile_source_rule",
        ),
        UniqueConstraint(
            "dataset_id",
            "academic_unit_key",
            "effective_year",
            name="uq_graduation_assessment_profile_scope",
        ),
        CheckConstraint(
            "effective_year BETWEEN 1900 AND 2100",
            name="ck_graduation_assessment_effective_year",
        ),
        CheckConstraint(
            "transition_mode IN ('STANDARDIZED_ONLY', 'LEGACY_OR_STANDARDIZED', 'LEGACY_ONLY')",
            name="ck_graduation_assessment_transition_mode",
        ),
        Index(
            "ix_graduation_assessment_profile_lookup",
            "academic_unit_key",
            "effective_year",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("requirement_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_rule_id: Mapped[str] = mapped_column(String(160), nullable=False)
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_unit: Mapped[str] = mapped_column(String(240), nullable=False)
    academic_unit_key: Mapped[str] = mapped_column(String(240), nullable=False)
    transition_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    transition_source_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_note: Mapped[str | None] = mapped_column(Text)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GraduationAssessmentSourceReference(Base):
    __tablename__ = "graduation_assessment_source_refs"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "source_ref",
            name="uq_graduation_assessment_source_ref",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_assessment_source_ref_position"),
    )

    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_assessment_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)


class GraduationAssessmentCategory(Base):
    __tablename__ = "graduation_assessment_categories"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "category_code",
            name="uq_graduation_assessment_category",
        ),
        CheckConstraint(
            "category_code IN ('A', 'C', 'E', 'S')",
            name="ck_graduation_assessment_category_code",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_assessment_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_code: Mapped[str] = mapped_column(String(1), nullable=False)
    category_name: Mapped[str] = mapped_column(String(240), nullable=False)
    primary_none: Mapped[str | None] = mapped_column(Text)
    primary_one: Mapped[str | None] = mapped_column(Text)
    primary_two: Mapped[str | None] = mapped_column(Text)
    double_major_none: Mapped[str | None] = mapped_column(Text)
    double_major_one: Mapped[str | None] = mapped_column(Text)
    requirement_detail: Mapped[str | None] = mapped_column(Text)
    reference_note: Mapped[str | None] = mapped_column(Text)
    source_note: Mapped[str | None] = mapped_column(Text)


class GraduationAssessmentCredential(Base):
    __tablename__ = "graduation_assessment_credentials"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "position",
            name="uq_graduation_assessment_credential_position",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_assessment_credential_position"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_assessment_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    international_or_national_certification: Mapped[str | None] = mapped_column(Text)
    private_or_other_certification: Mapped[str | None] = mapped_column(Text)
    foreign_language: Mapped[str | None] = mapped_column(Text)
    awards: Mapped[str | None] = mapped_column(Text)
    employment_or_experience: Mapped[str | None] = mapped_column(Text)
    double_major_requirement: Mapped[str | None] = mapped_column(Text)
    reference_note: Mapped[str | None] = mapped_column(Text)
    source_note: Mapped[str | None] = mapped_column(Text)


class GraduationLegacyRequirement(Base):
    __tablename__ = "graduation_legacy_requirements"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "source_rule_id",
            name="uq_graduation_legacy_requirement_source_rule",
        ),
        CheckConstraint(
            "effective_year BETWEEN 1900 AND 2100",
            name="ck_graduation_legacy_effective_year",
        ),
        Index(
            "ix_graduation_legacy_requirement_lookup",
            "academic_unit_key",
            "effective_year",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(80),
        ForeignKey("requirement_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_rule_id: Mapped[str] = mapped_column(String(160), nullable=False)
    effective_year: Mapped[int] = mapped_column(Integer, nullable=False)
    academic_unit: Mapped[str] = mapped_column(String(240), nullable=False)
    academic_unit_key: Mapped[str] = mapped_column(String(240), nullable=False)
    eligibility_requirement: Mapped[str | None] = mapped_column(Text)
    form_thesis: Mapped[bool] = mapped_column(Boolean, nullable=False)
    form_report: Mapped[bool] = mapped_column(Boolean, nullable=False)
    form_practical_or_artwork: Mapped[bool] = mapped_column(Boolean, nullable=False)
    form_exam: Mapped[bool] = mapped_column(Boolean, nullable=False)
    substitute_international_certification: Mapped[str | None] = mapped_column(Text)
    substitute_national_technical_certification: Mapped[str | None] = mapped_column(Text)
    substitute_national_professional_certification: Mapped[str | None] = mapped_column(Text)
    substitute_national_accredited_private_certification: Mapped[str | None] = mapped_column(Text)
    substitute_private_certification: Mapped[str | None] = mapped_column(Text)
    substitute_other: Mapped[str | None] = mapped_column(Text)
    pass_requirement: Mapped[str | None] = mapped_column(Text)
    double_major_pass_requirement: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False)


class GraduationLegacySourceReference(Base):
    __tablename__ = "graduation_legacy_source_refs"
    __table_args__ = (
        UniqueConstraint(
            "legacy_requirement_id",
            "source_ref",
            name="uq_graduation_legacy_source_ref",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_legacy_source_ref_position"),
    )

    legacy_requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_legacy_requirements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_ref: Mapped[str] = mapped_column(Text, nullable=False)


class GraduationLegacyCohort(Base):
    __tablename__ = "graduation_legacy_cohorts"
    __table_args__ = (
        UniqueConstraint(
            "legacy_requirement_id",
            "expression",
            name="uq_graduation_legacy_cohort_expression",
        ),
        UniqueConstraint(
            "legacy_requirement_id",
            "position",
            name="uq_graduation_legacy_cohort_position",
        ),
        CheckConstraint("position >= 0", name="ck_graduation_legacy_cohort_position"),
        CheckConstraint(
            "start_year IS NULL OR end_year IS NULL OR start_year <= end_year",
            name="ck_graduation_legacy_cohort_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    legacy_requirement_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("graduation_legacy_requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    start_year: Mapped[int | None] = mapped_column(Integer)
    end_year: Mapped[int | None] = mapped_column(Integer)
    expression: Mapped[str] = mapped_column(String(160), nullable=False)


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
