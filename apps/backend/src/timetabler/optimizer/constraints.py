"""Shared hard-constraint predicates for production and reference solvers."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

from .models import OptimizationRequest, Section, Session


class InvalidProblemError(ValueError):
    """Raised when an optimizer request violates the normalized input contract."""


def sessions_overlap(left: Session, right: Session) -> bool:
    """Return whether two half-open intervals overlap on the same day."""

    return (
        left.day == right.day
        and left.start_minute < right.end_minute
        and right.start_minute < left.end_minute
    )


def sections_conflict(left: Section, right: Section) -> bool:
    return any(sessions_overlap(a, b) for a in left.sessions for b in right.sessions)


def validate_request(request: OptimizationRequest) -> None:
    """Validate identifiers and invariants that indicate malformed input."""

    ids = [section.section_id for section in request.sections]
    duplicates = sorted(section_id for section_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        raise InvalidProblemError(f"duplicate section ids: {', '.join(duplicates)}")

    section_by_id = {section.section_id: section for section in request.sections}
    referenced_ids = (
        request.locked_section_ids | request.current_section_ids | request.excluded_section_ids
    )
    unknown_ids = referenced_ids - section_by_id.keys()
    if unknown_ids:
        raise InvalidProblemError(f"unknown section ids: {', '.join(sorted(unknown_ids))}")

    locked_courses = [
        section_by_id[section_id].course_id for section_id in request.locked_section_ids
    ]
    duplicate_locked_courses = sorted(
        course for course, count in Counter(locked_courses).items() if count > 1
    )
    if duplicate_locked_courses:
        raise InvalidProblemError(
            f"multiple locked sections for the same course: {', '.join(duplicate_locked_courses)}"
        )

    current_courses = [
        section_by_id[section_id].course_id for section_id in request.current_section_ids
    ]
    duplicate_current_courses = sorted(
        course for course, count in Counter(current_courses).items() if count > 1
    )
    if duplicate_current_courses:
        raise InvalidProblemError(
            "multiple current sections for the same course: " + ", ".join(duplicate_current_courses)
        )

    for section in request.sections:
        for left, right in combinations(section.sessions, 2):
            if sessions_overlap(left, right):
                raise InvalidProblemError(
                    f"section {section.section_id} contains overlapping meetings"
                )


def selection_is_feasible(request: OptimizationRequest, selected: tuple[Section, ...]) -> bool:
    """Evaluate every documented hard constraint for a concrete selection."""

    selected_ids = {section.section_id for section in selected}
    selected_courses = {section.course_id for section in selected}

    if len(selected_courses) != len(selected):
        return False
    if request.locked_section_ids - selected_ids:
        return False
    if selected_ids & request.excluded_section_ids:
        return False
    if request.required_course_ids - selected_courses:
        return False
    if any(section.verified_eligible is False for section in selected):
        return False
    if any(
        session.day in request.preferences.excluded_days
        or (
            request.preferences.hard_earliest_start_minute is not None
            and session.start_minute < request.preferences.hard_earliest_start_minute
        )
        or (
            request.preferences.hard_latest_end_minute is not None
            and session.end_minute > request.preferences.hard_latest_end_minute
        )
        for section in selected
        for session in section.sessions
    ):
        return False

    credits = sum(section.credits for section in selected)
    if not request.min_credits <= credits <= request.max_credits:
        return False

    for group in request.required_groups:
        if len(selected_courses & group.course_ids) < group.minimum_courses:
            return False

    if request.preferences.max_gap_minutes is not None:
        meetings_by_day: dict[int, list[Session]] = defaultdict(list)
        for section in selected:
            for meeting in section.sessions:
                meetings_by_day[meeting.day].append(meeting)
        for meetings in meetings_by_day.values():
            first = min(meeting.start_minute for meeting in meetings)
            last = max(meeting.end_minute for meeting in meetings)
            occupied = sum(meeting.end_minute - meeting.start_minute for meeting in meetings)
            if last - first - occupied > request.preferences.max_gap_minutes:
                return False

    return not any(sections_conflict(left, right) for left, right in combinations(selected, 2))


def infeasibility_hints(request: OptimizationRequest) -> tuple[str, ...]:
    """Return safe, user-facing relaxations without pretending to prove an IIS."""

    section_by_id = {section.section_id: section for section in request.sections}
    available_courses = {
        section.course_id
        for section in request.sections
        if section.verified_eligible is not False
        and section.section_id not in request.excluded_section_ids
    }
    hints: list[str] = []

    missing_courses = request.required_course_ids - available_courses
    if missing_courses:
        hints.append(f"필수 과목 후보를 추가하세요: {', '.join(sorted(missing_courses))}")

    for group in request.required_groups:
        available = len(group.course_ids & available_courses)
        if available < group.minimum_courses:
            hints.append(f"{group.group_id} 그룹의 필수 개수를 줄이거나 후보 과목을 추가하세요")

    locked = [section_by_id[section_id] for section_id in request.locked_section_ids]
    conflicting_locked = [
        (left.section_id, right.section_id)
        for left, right in combinations(locked, 2)
        if sections_conflict(left, right)
    ]
    if conflicting_locked:
        hints.append("서로 겹치는 잠금 분반 중 하나를 잠금 해제하세요")

    locked_credits = sum(section.credits for section in locked)
    if locked_credits > request.max_credits:
        hints.append("최대 학점을 늘리거나 잠금 분반을 줄이세요")

    if not hints:
        hints.append("학점 범위, 잠금, 필수 과목 또는 시간 조건 중 하나를 완화하세요")
    return tuple(hints)
