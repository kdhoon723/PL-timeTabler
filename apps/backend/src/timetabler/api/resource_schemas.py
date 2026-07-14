from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from timetabler.catalog.models import Day, Section
from timetabler.types import APIModel


class UserRead(APIModel):
    id: str
    student_number: str
    name: str | None
    grade: int | None
    department: str | None
    admission_year: int | None
    entry_type: str | None
    student_type: str | None
    section_group: str | None
    major_path: str | None
    profile_completed: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    grade: int | None = Field(default=None, ge=1, le=4)
    department: str | None = Field(default=None, min_length=1, max_length=200)
    admission_year: int | None = Field(default=None, ge=1990, le=2100)
    entry_type: Literal["FRESHMAN", "TRANSFER"] | None = None
    student_type: Literal["DOMESTIC", "INTERNATIONAL", "UNKNOWN"] | None = None
    section_group: Literal["ODD", "EVEN", "UNKNOWN"] | None = None
    major_path: Literal["ADVANCED_MAJOR", "DOUBLE_MAJOR", "MINOR", "MICRO_MAJOR"] | None = None

    @model_validator(mode="after")
    def require_update(self) -> UserUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one user field is required")
        return self


class ConsentCreate(APIModel):
    consent_version: str = Field(min_length=1, max_length=40)
    agreed: bool


class ConsentRead(APIModel):
    id: str
    consent_version: str
    agreed: bool
    agreed_at: datetime


class UserDeleteRequest(APIModel):
    confirmation: str


class DeleteResponse(APIModel):
    message: str
    deleted_at: datetime | None = None


class TimetableItem(APIModel):
    section_id: str = Field(min_length=1, max_length=100)
    role: Literal["must", "want", "backup", "exclude"] = "want"
    locked: bool = False
    professor_locked: bool = False


class TimetablePreferences(APIModel):
    target_credits: int = Field(default=18, ge=0, le=30)
    min_credits: int = Field(default=15, ge=0, le=30)
    max_credits: int = Field(default=21, ge=0, le=30)
    preferred_free_days: tuple[Day, ...] = ()
    excluded_days: tuple[Day, ...] = ()
    avoid_before: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    avoid_after: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    hard_start: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    hard_end: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    max_gap_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    min_lunch_minutes: int = Field(default=60, ge=0, le=150)
    max_daily_minutes: int = Field(default=360, gt=0, le=24 * 60)
    compactness: int = Field(default=70, ge=0, le=100)
    minimize_changes: bool = True

    @model_validator(mode="after")
    def validate_preferences(self) -> TimetablePreferences:
        if not self.min_credits <= self.target_credits <= self.max_credits:
            raise ValueError("targetCredits must be between minCredits and maxCredits")
        if len(set(self.preferred_free_days)) != len(self.preferred_free_days):
            raise ValueError("preferredFreeDays contains duplicates")
        if len(set(self.excluded_days)) != len(self.excluded_days):
            raise ValueError("excludedDays contains duplicates")
        if set(self.preferred_free_days) & set(self.excluded_days):
            raise ValueError("preferredFreeDays and excludedDays must be disjoint")
        if self.hard_start and self.hard_end and self.hard_start >= self.hard_end:
            raise ValueError("hardStart must be before hardEnd")
        return self


class TimetableCreate(APIModel):
    name: str = Field(min_length=1, max_length=120)
    semester: str = Field(min_length=1, max_length=20)
    data_version: str | None = Field(default=None, max_length=80)
    items: tuple[TimetableItem, ...] = ()
    preferences: TimetablePreferences = Field(default_factory=TimetablePreferences)


class TimetableUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    data_version: str | None = Field(default=None, max_length=80)
    preferences: TimetablePreferences | None = None

    @model_validator(mode="after")
    def require_update(self) -> TimetableUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one timetable field is required")
        return self


class TimetableItemsUpdate(APIModel):
    items: tuple[TimetableItem, ...]
    data_version: str | None = Field(default=None, max_length=80)


class TimetableFavoriteUpdate(APIModel):
    favorite: bool


class TimetableCopyRequest(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)


class TimetableRead(APIModel):
    id: str
    name: str
    semester: str
    data_version: str | None
    items: tuple[TimetableItem, ...]
    preferences: TimetablePreferences
    favorite: bool
    created_at: datetime
    updated_at: datetime


class TimetableMetrics(APIModel):
    credits: float
    campus_days: int
    gap_minutes: int


class TimetableDetail(APIModel):
    timetable: TimetableRead
    sections: tuple[Section, ...]
    metrics: TimetableMetrics
    conflict_section_ids: tuple[tuple[str, str], ...]


class TimetableList(APIModel):
    timetables: tuple[TimetableRead, ...]
    total: int


class TimetableShareCreate(APIModel):
    expires_at: datetime | None = None


class TimetableShareRead(APIModel):
    share_code: str
    share_url: str
    expires_at: datetime | None


class SharedTimetableRead(APIModel):
    timetable: TimetableRead
    sections: tuple[Section, ...]
    metrics: TimetableMetrics


class ReviewCreate(APIModel):
    professor: str | None = Field(default=None, max_length=120)
    semester: str = Field(min_length=1, max_length=20)
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=2000)


class ReviewUpdate(APIModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    content: str | None = Field(default=None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def require_update(self) -> ReviewUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one review field is required")
        return self


class ReviewRead(APIModel):
    id: str
    course_code: str
    course_name: str
    professor: str | None
    semester: str
    rating: int
    content: str
    mine: bool
    created_at: datetime
    updated_at: datetime


class RatingSummary(APIModel):
    average_rating: float
    review_count: int
    popularity_score: float


class ReviewList(APIModel):
    reviews: tuple[ReviewRead, ...]
    rating_summary: RatingSummary
    total: int


class ReviewMutationResponse(APIModel):
    review: ReviewRead
    rating_summary: RatingSummary


class ReviewDeleteResponse(APIModel):
    message: str
    rating_summary: RatingSummary


CompletedStatus = Literal["IN_PROGRESS", "COMPLETED"]


class CompletedCourseCreate(APIModel):
    course_code: str | None = Field(default=None, max_length=40)
    course_name: str = Field(min_length=1, max_length=240)
    credits: float = Field(gt=0, le=30)
    category: str = Field(min_length=1, max_length=160)
    area: str | None = Field(default=None, max_length=120)
    semester: str | None = Field(default=None, max_length=20)
    status: CompletedStatus = "COMPLETED"


class CompletedCourseUpdate(APIModel):
    course_code: str | None = Field(default=None, max_length=40)
    course_name: str | None = Field(default=None, min_length=1, max_length=240)
    credits: float | None = Field(default=None, gt=0, le=30)
    category: str | None = Field(default=None, min_length=1, max_length=160)
    area: str | None = Field(default=None, max_length=120)
    semester: str | None = Field(default=None, max_length=20)
    status: CompletedStatus | None = None

    @model_validator(mode="after")
    def require_update(self) -> CompletedCourseUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one completed-course field is required")
        return self


class CompletedCourseRead(APIModel):
    id: str
    course_code: str | None
    course_name: str
    credits: float
    category: str
    area: str | None
    semester: str | None
    status: CompletedStatus
    created_at: datetime
    updated_at: datetime


class CreditSummary(APIModel):
    total_credits: float
    major_credits: float
    liberal_credits: float
    area_credits: dict[str, float]


class CompletedCourseList(APIModel):
    completed_courses: tuple[CompletedCourseRead, ...]
    credit_summary: CreditSummary


class TimetableCourseImport(APIModel):
    timetable_id: str
    status: CompletedStatus = "IN_PROGRESS"


class TimetableCourseImportResponse(APIModel):
    imported_courses: tuple[CompletedCourseRead, ...]
    skipped_courses: tuple[str, ...]


class CourseSummaryRead(APIModel):
    course_code: str
    name: str
    category: str
    credits: float
    grade: int | None
    section_count: int
    professors: tuple[str, ...]
    average_rating: float
    review_count: int
    popularity_score: float


class CourseListRead(APIModel):
    courses: tuple[CourseSummaryRead, ...]
    page: int
    size: int
    total: int


class CourseDetailRead(APIModel):
    course: CourseSummaryRead
    sections: tuple[Section, ...]
    rating_summary: RatingSummary


class DepartmentRead(APIModel):
    id: str
    college: str
    name: str
    curriculum_url: str | None
    graduation_url: str | None


class DepartmentListRead(APIModel):
    departments: tuple[DepartmentRead, ...]


class SemesterVersionRead(APIModel):
    semester: str
    dataset_version: str
    updated_at: str


class RequirementProfile(APIModel):
    admission_year: int = Field(ge=1990, le=2100)
    department_id: str = Field(min_length=1, max_length=200)
    student_type: str = Field(min_length=1, max_length=40)
    program_path: str = Field(min_length=1, max_length=40)


class RequirementRuleList(APIModel):
    rules: tuple[dict[str, Any], ...]
    manual_review_items: tuple[str, ...]
    as_of: str


class RequirementStatus(APIModel):
    kind: str
    required: float | None
    current: float | None
    satisfied: bool | None
    missing: tuple[str, ...] = ()


class AreaStatus(APIModel):
    area: str
    credits: float
    satisfied: bool


class RequirementEvaluation(APIModel):
    credit_status: tuple[RequirementStatus, ...]
    area_status: tuple[AreaStatus, ...]
    required_course_status: tuple[RequirementStatus, ...]
    missing_requirements: tuple[str, ...]
    manual_review_items: tuple[str, ...]


class RequirementRecommendation(APIModel):
    missing_requirements: tuple[str, ...]
    recommended_courses: tuple[CourseSummaryRead, ...]


class RequirementSource(APIModel):
    source_id: str
    title: str
    url: str
    effective_date: str | None = None
    verified_at: str
