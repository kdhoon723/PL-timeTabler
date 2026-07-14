from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from timetabler.catalog.models import Day
from timetabler.types import APIModel


class HealthStatus(APIModel):
    status: str


class ReadinessStatus(APIModel):
    status: str
    catalog: str
    database: str


class OtpStartRequest(APIModel):
    student_number: str = Field(min_length=6, max_length=12, pattern=r"^\d{6,12}$")


class OtpVerifyRequest(APIModel):
    student_number: str = Field(min_length=6, max_length=12, pattern=r"^\d{6,12}$")
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class OtpStartResponse(APIModel):
    message: str


class AuthSessionRead(APIModel):
    available: bool
    authenticated: bool
    student_number: str | None = None
    expires_at: datetime | None = None


class OptimizationJobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIME_LIMIT = "TIME_LIMIT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OptimizationPreferences(APIModel):
    preferred_days_off: tuple[Day, ...] = ()
    excluded_days: tuple[Day, ...] = ()
    avoid_before_minute: int | None = Field(default=None, ge=0, lt=24 * 60)
    avoid_after_minute: int | None = Field(default=None, gt=0, le=24 * 60)
    hard_start_minute: int | None = Field(default=None, ge=0, lt=24 * 60)
    hard_end_minute: int | None = Field(default=None, gt=0, le=24 * 60)
    max_gap_minutes: int | None = Field(default=None, ge=0, le=24 * 60)
    minimize_campus_days: bool = True
    minimize_gap_minutes: bool = True
    gap_weight_percent: int = Field(default=50, ge=0, le=100)
    minimize_changes: bool = True
    max_daily_minutes: int | None = Field(default=None, gt=0, le=24 * 60)
    min_lunch_minutes: int = Field(default=0, ge=0, le=150)

    @model_validator(mode="after")
    def validate_days_off(self) -> OptimizationPreferences:
        if len(set(self.preferred_days_off)) != len(self.preferred_days_off):
            raise ValueError("preferredDaysOff contains duplicates")
        if len(set(self.excluded_days)) != len(self.excluded_days):
            raise ValueError("excludedDays contains duplicates")
        if set(self.preferred_days_off) & set(self.excluded_days):
            raise ValueError("preferredDaysOff and excludedDays must be disjoint")
        if (
            self.hard_start_minute is not None
            and self.hard_end_minute is not None
            and self.hard_start_minute >= self.hard_end_minute
        ):
            raise ValueError("hardStartMinute must be before hardEndMinute")
        return self


class ProfessorConstraint(APIModel):
    course_code: str = Field(min_length=1, max_length=32)
    professor: str = Field(min_length=1, max_length=120)


class OptimizationCreate(APIModel):
    semester: str = "2026-1"
    dataset_version: str
    required_course_codes: tuple[str, ...] = ()
    candidate_course_codes: tuple[str, ...] = ()
    excluded_course_codes: tuple[str, ...] = ()
    locked_section_ids: tuple[str, ...] = ()
    selected_section_ids: tuple[str, ...] = ()
    professor_constraints: tuple[ProfessorConstraint, ...] = ()
    # The current Daejin catalog and optimizer use whole-credit units. Reject
    # fractional transport values instead of silently rounding relaxed bounds.
    min_credits: int = Field(default=12, ge=0, le=30, strict=True)
    max_credits: int = Field(default=18, ge=0, le=30, strict=True)
    target_credits: int | None = Field(default=None, ge=0, le=30, strict=True)
    preferences: OptimizationPreferences = Field(default_factory=OptimizationPreferences)
    candidate_count: int = Field(default=3, ge=1, le=5)
    seed: int = Field(default=0, ge=0, le=2_147_483_647)
    time_limit_seconds: float = Field(default=3, gt=0, le=8)

    @model_validator(mode="after")
    def validate_intents(self) -> OptimizationCreate:
        required = set(self.required_course_codes)
        candidates = set(self.candidate_course_codes)
        excluded = set(self.excluded_course_codes)
        if self.min_credits > self.max_credits:
            raise ValueError("minCredits must not exceed maxCredits")
        if self.target_credits is not None and not (
            self.min_credits <= self.target_credits <= self.max_credits
        ):
            raise ValueError("targetCredits must be between minCredits and maxCredits")
        if required & excluded:
            raise ValueError("requiredCourseCodes and excludedCourseCodes must be disjoint")
        if candidates & excluded:
            raise ValueError("candidateCourseCodes and excludedCourseCodes must be disjoint")
        if len(required) != len(self.required_course_codes):
            raise ValueError("requiredCourseCodes contains duplicates")
        professor_courses = [constraint.course_code for constraint in self.professor_constraints]
        if len(set(professor_courses)) != len(professor_courses):
            raise ValueError("professorConstraints contains duplicate course codes")
        return self


class CandidateMetrics(APIModel):
    total_credits: float
    campus_days: int
    gap_minutes: int
    first_class_minute: int | None
    last_class_minute: int | None
    target_credit_deviation: float = 0
    unknown_time_sections: int = 0


class CandidateCompareRequest(APIModel):
    current_section_ids: tuple[str, ...] = ()
    candidate_section_ids: tuple[tuple[str, ...], ...] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def validate_candidates(self) -> CandidateCompareRequest:
        if len(set(self.current_section_ids)) != len(self.current_section_ids):
            raise ValueError("currentSectionIds contains duplicates")
        if any(len(set(candidate)) != len(candidate) for candidate in self.candidate_section_ids):
            raise ValueError("candidateSectionIds contains duplicate section ids")
        return self


class CandidateSwapRead(APIModel):
    from_section_id: str
    to_section_id: str


class CandidateComparisonRead(APIModel):
    rank: int = Field(ge=1)
    section_ids: tuple[str, ...]
    metrics: CandidateMetrics
    added: tuple[str, ...]
    removed: tuple[str, ...]
    swapped: tuple[CandidateSwapRead, ...]
    conflicts: tuple[tuple[str, str], ...]


class CandidateCompareResponse(APIModel):
    candidates: tuple[CandidateComparisonRead, ...]


class OptimizationCandidate(APIModel):
    rank: int = Field(ge=1)
    section_ids: tuple[str, ...]
    metrics: CandidateMetrics
    score_components: dict[str, int]
    changes: tuple[str, ...] = ()
    unmet_preferences: tuple[str, ...] = ()
    explanation: tuple[str, ...] = ()


class OptimizationResult(APIModel):
    solver_version: str
    candidates: tuple[OptimizationCandidate, ...] = ()
    reasons: tuple[str, ...] = ()


class OptimizationJobRead(APIModel):
    id: str
    status: OptimizationJobStatus
    request: OptimizationCreate
    result: OptimizationResult | None = None
    error_code: str | None = None
    error_message: str | None = None
    cancel_requested: bool
    attempts: int
    created_at: datetime
    updated_at: datetime
