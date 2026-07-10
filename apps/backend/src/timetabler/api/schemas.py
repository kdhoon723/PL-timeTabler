from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from timetabler.types import APIModel


class HealthStatus(APIModel):
    status: str


class ReadinessStatus(APIModel):
    status: str
    catalog: str
    database: str


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
    preferred_days_off: tuple[str, ...] = ()
    avoid_before_minute: int | None = Field(default=None, ge=0, lt=24 * 60)
    avoid_after_minute: int | None = Field(default=None, gt=0, le=24 * 60)
    minimize_campus_days: bool = True
    minimize_gap_minutes: bool = True
    max_daily_minutes: int | None = Field(default=None, gt=0, le=24 * 60)


class OptimizationCreate(APIModel):
    semester: str = "2026-1"
    dataset_version: str
    required_course_codes: tuple[str, ...] = ()
    candidate_course_codes: tuple[str, ...] = ()
    excluded_course_codes: tuple[str, ...] = ()
    locked_section_ids: tuple[str, ...] = ()
    selected_section_ids: tuple[str, ...] = ()
    min_credits: float = Field(default=12, ge=0, le=30)
    max_credits: float = Field(default=18, ge=0, le=30)
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
        if required & excluded:
            raise ValueError("requiredCourseCodes and excludedCourseCodes must be disjoint")
        if candidates & excluded:
            raise ValueError("candidateCourseCodes and excludedCourseCodes must be disjoint")
        if len(required) != len(self.required_course_codes):
            raise ValueError("requiredCourseCodes contains duplicates")
        return self


class CandidateMetrics(APIModel):
    total_credits: float
    campus_days: int
    gap_minutes: int
    first_class_minute: int | None
    last_class_minute: int | None


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
