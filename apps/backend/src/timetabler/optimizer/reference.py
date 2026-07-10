"""Small-fixture reference optimizer used as a correctness oracle."""

from __future__ import annotations

from collections import defaultdict
from time import monotonic

from .constraints import infeasibility_hints, selection_is_feasible, validate_request
from .models import (
    Candidate,
    OptimizationRequest,
    OptimizationResult,
    Section,
    SolverStatus,
)
from .scoring import build_candidate


class BacktrackingOptimizer:
    """Exhaustive deterministic solver for tests and small validation fixtures only."""

    def __init__(self, *, max_states: int = 200_000) -> None:
        if max_states < 1:
            raise ValueError("max_states must be positive")
        self._max_states = max_states

    def solve(self, request: OptimizationRequest) -> OptimizationResult:
        started = monotonic()
        try:
            validate_request(request)
        except ValueError as exc:
            return OptimizationResult(
                status=SolverStatus.FAILED,
                wall_time_seconds=monotonic() - started,
                error=str(exc),
            )

        deadline = started + request.time_limit_seconds
        sections_by_course: dict[str, list[Section]] = defaultdict(list)
        for section in request.sections:
            if (
                section.section_id in request.excluded_section_ids
                or section.verified_eligible is False
            ):
                continue
            sections_by_course[section.course_id].append(section)
        for sections in sections_by_course.values():
            sections.sort(key=lambda section: section.section_id)

        locked_by_course = {
            section.course_id: section
            for section in request.sections
            if section.section_id in request.locked_section_ids
        }
        courses = sorted(sections_by_course)
        feasible: list[Candidate] = []
        explored_states = 0
        stopped_early = False

        def search(index: int, selected: list[Section], credits: int) -> None:
            nonlocal explored_states, stopped_early
            if stopped_early:
                return
            if monotonic() >= deadline or explored_states >= self._max_states:
                stopped_early = True
                return
            explored_states += 1

            if credits > request.max_credits:
                return
            if index == len(courses):
                selection = tuple(selected)
                if selection_is_feasible(request, selection):
                    feasible.append(build_candidate(request, selection, rank=0))
                return

            course_id = courses[index]
            locked = locked_by_course.get(course_id)
            options: tuple[Section | None, ...] = (
                (locked,) if locked is not None else (None, *sections_by_course[course_id])
            )

            for option in options:
                if option is None:
                    search(index + 1, selected, credits)
                else:
                    selected.append(option)
                    search(index + 1, selected, credits + option.credits)
                    selected.pop()

        search(0, [], 0)
        feasible.sort(
            key=lambda candidate: (
                candidate.score.weighted_score,
                candidate.section_ids,
            )
        )
        candidates = _select_diverse_candidates(feasible, request)
        candidates = tuple(
            Candidate(
                rank=rank,
                section_ids=candidate.section_ids,
                course_ids=candidate.course_ids,
                total_credits=candidate.total_credits,
                score=candidate.score,
                changed_course_ids=candidate.changed_course_ids,
                unmet_preferences=candidate.unmet_preferences,
            )
            for rank, candidate in enumerate(candidates, start=1)
        )

        if stopped_early:
            status = SolverStatus.TIME_LIMIT
        elif candidates:
            status = SolverStatus.OPTIMAL
        else:
            status = SolverStatus.INFEASIBLE
        return OptimizationResult(
            status=status,
            candidates=candidates,
            wall_time_seconds=monotonic() - started,
            explored_states=explored_states,
            relaxations=infeasibility_hints(request) if status is SolverStatus.INFEASIBLE else (),
        )


def _select_diverse_candidates(
    ordered: list[Candidate], request: OptimizationRequest
) -> tuple[Candidate, ...]:
    selected: list[Candidate] = []
    for candidate in ordered:
        ids = set(candidate.section_ids)
        if all(
            len(ids.symmetric_difference(existing.section_ids))
            >= request.minimum_candidate_difference
            for existing in selected
        ):
            selected.append(candidate)
        if len(selected) == request.max_candidates:
            break
    return tuple(selected)
