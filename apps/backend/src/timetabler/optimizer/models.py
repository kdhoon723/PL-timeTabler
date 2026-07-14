"""Normalized optimizer input and output models.

Raw catalog parsing intentionally lives outside the optimizer boundary.  In
particular, ``lectTm`` strings and nullable room joins must be normalized by the
catalog layer before constructing these dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class SolverStatus(StrEnum):
    """Solver status, kept distinct from persistent optimization job states."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIME_LIMIT = "TIME_LIMIT"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True, order=True)
class Session:
    """One normalized half-open meeting interval ``[start, end)``.

    ``day`` uses ISO weekday numbering (Monday=0 through Sunday=6).  Adjacent
    intervals therefore do not conflict.  ``location_group`` is optional because
    the supplied classroom dataset does not cover every section.
    """

    day: int
    start_minute: int
    end_minute: int
    location_group: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.day <= 6:
            raise ValueError("session day must be between 0 and 6")
        if not 0 <= self.start_minute < self.end_minute <= 24 * 60:
            raise ValueError("session must have a valid start/end minute")


@dataclass(frozen=True, slots=True)
class Section:
    """A selectable course section with already-normalized meetings."""

    section_id: str
    course_id: str
    credits: int
    sessions: tuple[Session, ...] = ()
    instructor: str | None = None
    # ``None`` means the restriction is unverified and MUST NOT be hard-enforced.
    verified_eligible: bool | None = None

    def __post_init__(self) -> None:
        if not self.section_id or not self.course_id:
            raise ValueError("section_id and course_id are required")
        if self.credits < 0:
            raise ValueError("section credits cannot be negative")
        object.__setattr__(self, "sessions", tuple(sorted(self.sessions)))


@dataclass(frozen=True, slots=True)
class RequiredGroup:
    """Require at least ``minimum_courses`` distinct courses from a verified group."""

    group_id: str
    course_ids: frozenset[str]
    minimum_courses: int = 1

    def __post_init__(self) -> None:
        if not self.group_id or not self.course_ids:
            raise ValueError("required group must have an id and course ids")
        if not 1 <= self.minimum_courses <= len(self.course_ids):
            raise ValueError("minimum_courses must fit inside the required group")


@dataclass(frozen=True, slots=True)
class Preferences:
    """User-controlled soft preferences."""

    preferred_days_off: frozenset[int] = frozenset()
    avoided_days: frozenset[int] = frozenset()
    excluded_days: frozenset[int] = frozenset()
    earliest_start_minute: int | None = None
    latest_end_minute: int | None = None
    hard_earliest_start_minute: int | None = None
    hard_latest_end_minute: int | None = None
    max_gap_minutes: int | None = None
    max_campus_days: int | None = None
    max_daily_minutes: int | None = None
    min_lunch_minutes: int = 0
    gap_weight_percent: int = 50
    minimize_changes: bool = True

    def __post_init__(self) -> None:
        for day in self.preferred_days_off | self.avoided_days | self.excluded_days:
            if not 0 <= day <= 6:
                raise ValueError("preference day must be between 0 and 6")
        if (
            self.earliest_start_minute is not None
            and not 0 <= self.earliest_start_minute <= 24 * 60
        ):
            raise ValueError("earliest_start_minute must be within a day")
        if self.latest_end_minute is not None and not 0 <= self.latest_end_minute <= 24 * 60:
            raise ValueError("latest_end_minute must be within a day")
        if self.hard_earliest_start_minute is not None and not (
            0 <= self.hard_earliest_start_minute < 24 * 60
        ):
            raise ValueError("hard_earliest_start_minute must be within a day")
        if self.hard_latest_end_minute is not None and not (
            0 < self.hard_latest_end_minute <= 24 * 60
        ):
            raise ValueError("hard_latest_end_minute must be within a day")
        if (
            self.hard_earliest_start_minute is not None
            and self.hard_latest_end_minute is not None
            and self.hard_earliest_start_minute >= self.hard_latest_end_minute
        ):
            raise ValueError("hard time bounds are invalid")
        if self.max_gap_minutes is not None and not 0 <= self.max_gap_minutes <= 24 * 60:
            raise ValueError("max_gap_minutes must be within a day")
        if self.max_campus_days is not None and not 0 <= self.max_campus_days <= 7:
            raise ValueError("max_campus_days must be between 0 and 7")
        if self.max_daily_minutes is not None and not 0 < self.max_daily_minutes <= 24 * 60:
            raise ValueError("max_daily_minutes must be greater than 0 and within a day")
        if not 0 <= self.min_lunch_minutes <= 150:
            raise ValueError("min_lunch_minutes must be between 0 and 150")
        if not 0 <= self.gap_weight_percent <= 100:
            raise ValueError("gap_weight_percent must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class ObjectiveWeights:
    """Integer weights make the solver objective reproducible and inspectable."""

    campus_day: int = 600
    preferred_day_off: int = 800
    gap_minute: int = 1
    early_minute: int = 2
    late_minute: int = 2
    avoided_day: int = 500
    section_change: int = 300
    unknown_time: int = 250
    movement_transition: int = 60
    daily_overflow_minute: int = 4
    lunch_shortage_minute: int = 3
    target_credit: int = 200

    def __post_init__(self) -> None:
        if any(value < 0 for value in self.as_tuple()):
            raise ValueError("objective weights cannot be negative")

    def as_tuple(self) -> tuple[int, ...]:
        return (
            self.campus_day,
            self.preferred_day_off,
            self.gap_minute,
            self.early_minute,
            self.late_minute,
            self.avoided_day,
            self.section_change,
            self.unknown_time,
            self.movement_transition,
            self.daily_overflow_minute,
            self.lunch_shortage_minute,
            self.target_credit,
        )


@dataclass(frozen=True, slots=True)
class OptimizationRequest:
    """A complete, side-effect-free optimization problem."""

    sections: tuple[Section, ...]
    min_credits: int = 0
    max_credits: int = 30
    target_credits: int | None = None
    locked_section_ids: frozenset[str] = frozenset()
    required_course_ids: frozenset[str] = frozenset()
    required_groups: tuple[RequiredGroup, ...] = ()
    current_section_ids: frozenset[str] = frozenset()
    excluded_section_ids: frozenset[str] = frozenset()
    preferences: Preferences = field(default_factory=Preferences)
    weights: ObjectiveWeights = field(default_factory=ObjectiveWeights)
    max_candidates: int = 3
    minimum_candidate_difference: int = 1
    time_limit_seconds: float = 3.0
    seed: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "required_groups", tuple(self.required_groups))
        if self.min_credits < 0 or self.max_credits < self.min_credits:
            raise ValueError("credit bounds are invalid")
        if self.target_credits is not None and not (
            self.min_credits <= self.target_credits <= self.max_credits
        ):
            raise ValueError("target_credits must be within credit bounds")
        if self.max_candidates < 1:
            raise ValueError("max_candidates must be positive")
        if self.minimum_candidate_difference < 1:
            raise ValueError("minimum_candidate_difference must be positive")
        if not 0 < self.time_limit_seconds <= 8:
            raise ValueError("time_limit_seconds must be greater than 0 and at most 8")


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    """Transparent objective components returned with every candidate."""

    campus_days: int
    gap_minutes: int
    earliest_start_minute: int | None
    latest_end_minute: int | None
    early_minutes: int
    late_minutes: int
    preferred_day_off_violations: int
    avoided_day_sessions: int
    changed_courses: int
    unknown_time_sections: int
    movement_transitions: int
    daily_overflow_minutes: int
    lunch_shortage_minutes: int
    target_credit_deviation: int
    weighted_score: int


@dataclass(frozen=True, slots=True)
class Candidate:
    """One feasible timetable and the reasons behind its ranking."""

    rank: int
    section_ids: tuple[str, ...]
    course_ids: tuple[str, ...]
    total_credits: int
    score: ScoreBreakdown
    changed_course_ids: tuple[str, ...]
    unmet_preferences: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class OptimizationResult:
    """Pure solver result; the job worker maps this to persistent job state."""

    status: SolverStatus
    candidates: tuple[Candidate, ...] = ()
    wall_time_seconds: float = 0.0
    explored_states: int = 0
    relaxations: tuple[str, ...] = ()
    error: str | None = None
