"""Transparent candidate metrics and deterministic score calculation."""

from __future__ import annotations

from collections import defaultdict
from itertools import pairwise

from .models import Candidate, OptimizationRequest, ScoreBreakdown, Section, Session

PREFERENCE_PERCENT_BASE = 50
LUNCH_START_MINUTE = 11 * 60 + 30
LUNCH_END_MINUTE = 14 * 60


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
    for left, right in pairwise(sessions):
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


def _longest_lunch_break(sessions: list[Session]) -> int:
    """Return the longest continuous free interval in the lunch window."""

    cursor = LUNCH_START_MINUTE
    longest = 0
    for session in sessions:
        occupied_start = max(session.start_minute, LUNCH_START_MINUTE)
        occupied_end = min(session.end_minute, LUNCH_END_MINUTE)
        if occupied_start >= occupied_end:
            continue
        longest = max(longest, occupied_start - cursor)
        cursor = max(cursor, occupied_end)
    return max(longest, LUNCH_END_MINUTE - cursor)


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
    preferred_day_off_violations = len(set(daily) & request.preferences.preferred_days_off)
    avoided_day_sessions = sum(len(daily.get(day, ())) for day in request.preferences.avoided_days)

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
    daily_overflow_minutes = (
        sum(
            max(
                0,
                sum(session.end_minute - session.start_minute for session in sessions)
                - request.preferences.max_daily_minutes,
            )
            for sessions in daily.values()
        )
        if request.preferences.max_daily_minutes is not None
        else 0
    )
    lunch_shortage_minutes = 0
    if request.preferences.min_lunch_minutes:
        for sessions in daily.values():
            lunch_shortage_minutes += max(
                0,
                request.preferences.min_lunch_minutes - _longest_lunch_break(sessions),
            )

    total_credits = sum(section.credits for section in selected)
    target_credit_deviation = (
        abs(total_credits - request.target_credits) if request.target_credits is not None else 0
    )

    weights = request.weights
    fixed_score = (
        len(daily) * weights.campus_day
        + preferred_day_off_violations * weights.preferred_day_off
        + early_minutes * weights.early_minute
        + late_minutes * weights.late_minute
        + avoided_day_sessions * weights.avoided_day
        + unknown_time_sections * weights.unknown_time
        + movement_transitions * weights.movement_transition
        + daily_overflow_minutes * weights.daily_overflow_minute
        + lunch_shortage_minutes * weights.lunch_shortage_minute
    )
    if request.preferences.minimize_changes:
        fixed_score += len(changed_course_ids) * weights.section_change
    fixed_score += target_credit_deviation * weights.target_credit
    weighted_score = (
        fixed_score * PREFERENCE_PERCENT_BASE
        + gap_minutes * weights.gap_minute * request.preferences.gap_weight_percent
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
        daily_overflow_minutes=daily_overflow_minutes,
        lunch_shortage_minutes=lunch_shortage_minutes,
        target_credit_deviation=target_credit_deviation,
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
    if daily_overflow_minutes:
        unmet.append(f"하루 수업시간 목표를 총 {daily_overflow_minutes}분 초과했습니다")
    if lunch_shortage_minutes:
        unmet.append(f"점심 여유가 총 {lunch_shortage_minutes}분 부족합니다")
    if target_credit_deviation:
        unmet.append(f"목표 학점과 {target_credit_deviation}학점 차이가 있습니다")

    return Candidate(
        rank=rank,
        section_ids=tuple(section.section_id for section in selected),
        course_ids=tuple(section.course_id for section in selected),
        total_credits=total_credits,
        score=breakdown,
        changed_course_ids=changed_course_ids,
        unmet_preferences=tuple(unmet),
    )
