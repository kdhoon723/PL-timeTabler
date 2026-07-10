"""Transparent candidate metrics and deterministic score calculation."""

from __future__ import annotations

from collections import defaultdict

from .models import Candidate, OptimizationRequest, ScoreBreakdown, Section, Session


def _daily_sessions(sections: tuple[Section, ...]) -> dict[int, list[Session]]:
    result: dict[int, list[Session]] = defaultdict(list)
    for section in sections:
        for session in section.sessions:
            result[session.day].append(session)
    for sessions in result.values():
        sessions.sort(
            key=lambda session: (
                session.start_minute,
                session.end_minute,
                session.location_group or "",
            )
        )
    return dict(result)


def _gap_and_movement(sessions: list[Session]) -> tuple[int, int]:
    gap_minutes = 0
    movement_transitions = 0
    for left, right in zip(sessions, sessions[1:], strict=False):
        gap = max(0, right.start_minute - left.end_minute)
        gap_minutes += gap
        if (
            gap <= 30
            and left.location_group is not None
            and right.location_group is not None
            and left.location_group != right.location_group
        ):
            movement_transitions += 1
    return gap_minutes, movement_transitions


def build_candidate(
    request: OptimizationRequest,
    selected: tuple[Section, ...],
    *,
    rank: int,
) -> Candidate:
    """Build a stable candidate with exact metrics and Korean explanations."""

    selected = tuple(sorted(selected, key=lambda section: section.section_id))
    daily = _daily_sessions(selected)
    all_sessions = [session for sessions in daily.values() for session in sessions]
    gap_minutes = 0
    movement_transitions = 0
    for sessions in daily.values():
        daily_gap, daily_movement = _gap_and_movement(sessions)
        gap_minutes += daily_gap
        movement_transitions += daily_movement

    earliest = min((session.start_minute for session in all_sessions), default=None)
    latest = max((session.end_minute for session in all_sessions), default=None)
    early_minutes = (
        sum(
            max(0, request.preferences.earliest_start_minute - session.start_minute)
            for session in all_sessions
        )
        if request.preferences.earliest_start_minute is not None
        else 0
    )
    late_minutes = (
        sum(
            max(0, session.end_minute - request.preferences.latest_end_minute)
            for session in all_sessions
        )
        if request.preferences.latest_end_minute is not None
        else 0
    )
    preferred_day_off_violations = len(
        set(daily) & request.preferences.preferred_days_off
    )
    avoided_day_sessions = sum(
        len(daily.get(day, ())) for day in request.preferences.avoided_days
    )

    section_by_id = {section.section_id: section for section in request.sections}
    current_by_course = {
        section_by_id[section_id].course_id: section_id
        for section_id in request.current_section_ids
    }
    selected_by_course = {section.course_id: section.section_id for section in selected}
    changed_course_ids = tuple(
        sorted(
            course_id
            for course_id in current_by_course.keys() | selected_by_course.keys()
            if current_by_course.get(course_id) != selected_by_course.get(course_id)
        )
    )
    unknown_time_sections = sum(not section.sessions for section in selected)

    weights = request.weights
    weighted_score = (
        len(daily) * weights.campus_day
        + preferred_day_off_violations * weights.preferred_day_off
        + gap_minutes * weights.gap_minute
        + early_minutes * weights.early_minute
        + late_minutes * weights.late_minute
        + avoided_day_sessions * weights.avoided_day
        + len(changed_course_ids) * weights.section_change
        + unknown_time_sections * weights.unknown_time
        + movement_transitions * weights.movement_transition
    )
    breakdown = ScoreBreakdown(
        campus_days=len(daily),
        gap_minutes=gap_minutes,
        earliest_start_minute=earliest,
        latest_end_minute=latest,
        early_minutes=early_minutes,
        late_minutes=late_minutes,
        preferred_day_off_violations=preferred_day_off_violations,
        avoided_day_sessions=avoided_day_sessions,
        changed_courses=len(changed_course_ids),
        unknown_time_sections=unknown_time_sections,
        movement_transitions=movement_transitions,
        weighted_score=weighted_score,
    )

    unmet: list[str] = []
    if preferred_day_off_violations:
        unmet.append(f"원한 공강일 {preferred_day_off_violations}일에 수업이 있습니다")
    if early_minutes:
        unmet.append("원한 시작 시각보다 이른 수업이 있습니다")
    if late_minutes:
        unmet.append("원한 종료 시각보다 늦은 수업이 있습니다")
    if (
        request.preferences.max_campus_days is not None
        and len(daily) > request.preferences.max_campus_days
    ):
        unmet.append(
            f"등교일이 목표보다 {len(daily) - request.preferences.max_campus_days}일 많습니다"
        )
    if unknown_time_sections:
        unmet.append(f"시간 미정 분반이 {unknown_time_sections}개 있습니다")

    return Candidate(
        rank=rank,
        section_ids=tuple(section.section_id for section in selected),
        course_ids=tuple(section.course_id for section in selected),
        total_credits=sum(section.credits for section in selected),
        score=breakdown,
        changed_course_ids=changed_course_ids,
        unmet_preferences=tuple(unmet),
    )
