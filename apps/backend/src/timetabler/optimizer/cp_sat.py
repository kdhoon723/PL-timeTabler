"""Deterministic production CP-SAT timetable optimizer."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from time import monotonic
from typing import Any

from .constraints import infeasibility_hints, sections_conflict, validate_request
from .models import (
    Candidate,
    OptimizationRequest,
    OptimizationResult,
    Section,
    SolverStatus,
)
from .scoring import build_candidate

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - exercised only before backend dependencies install
    cp_model = None  # type: ignore[assignment]


class CpSatOptimizer:
    """Build and solve the production integer model without transport side effects."""

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
        if cp_model is None:
            return OptimizationResult(
                status=SolverStatus.FAILED,
                wall_time_seconds=monotonic() - started,
                error="OR-Tools is required to run CpSatOptimizer",
            )

        model, variables = self._build_model(request)
        candidates: list[Candidate] = []
        overall_status = SolverStatus.OPTIMAL
        explored_branches = 0

        for rank in range(1, request.max_candidates + 1):
            remaining = request.time_limit_seconds - (monotonic() - started)
            if remaining <= 0:
                overall_status = SolverStatus.TIME_LIMIT
                break

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = remaining
            solver.parameters.random_seed = request.seed
            solver.parameters.num_search_workers = 1
            status = solver.solve(model)
            explored_branches += solver.num_branches

            if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                selected = tuple(
                    section
                    for section in request.sections
                    if solver.boolean_value(variables[section.section_id])
                )
                candidates.append(build_candidate(request, selected, rank=rank))
                if status == cp_model.FEASIBLE:
                    overall_status = SolverStatus.FEASIBLE
                self._exclude_near_duplicate(model, variables, request, selected)
                continue

            if status == cp_model.INFEASIBLE:
                if not candidates:
                    overall_status = SolverStatus.INFEASIBLE
                break
            if status == cp_model.UNKNOWN:
                overall_status = SolverStatus.TIME_LIMIT
                break
            overall_status = SolverStatus.FAILED
            break

        # The model objective and exact public score use the same components, but
        # stable sorting also protects candidate ordering across OR-Tools patches.
        candidates.sort(
            key=lambda candidate: (
                candidate.score.weighted_score,
                candidate.section_ids,
            )
        )
        ranked = tuple(
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
        return OptimizationResult(
            status=overall_status,
            candidates=ranked,
            wall_time_seconds=monotonic() - started,
            explored_states=explored_branches,
            relaxations=infeasibility_hints(request)
            if overall_status is SolverStatus.INFEASIBLE
            else (),
            error="CP-SAT rejected the normalized model"
            if overall_status is SolverStatus.FAILED
            else None,
        )

    def _build_model(self, request: OptimizationRequest) -> tuple[Any, dict[str, Any]]:
        assert cp_model is not None
        model = cp_model.CpModel()
        variables = {
            section.section_id: model.new_bool_var(f"select_{section.section_id}")
            for section in request.sections
        }
        sections_by_course: dict[str, list[Section]] = defaultdict(list)
        for section in request.sections:
            sections_by_course[section.course_id].append(section)
            variable = variables[section.section_id]
            if (
                section.section_id in request.excluded_section_ids
                or section.verified_eligible is False
            ):
                model.add(variable == 0)
            if section.section_id in request.locked_section_ids:
                model.add(variable == 1)

        for sections in sections_by_course.values():
            model.add_at_most_one(variables[section.section_id] for section in sections)

        for course_id in request.required_course_ids:
            model.add(
                sum(
                    variables[section.section_id]
                    for section in sections_by_course.get(course_id, ())
                )
                == 1
            )
        for group in request.required_groups:
            model.add(
                sum(
                    variables[section.section_id]
                    for course_id in group.course_ids
                    for section in sections_by_course.get(course_id, ())
                )
                >= group.minimum_courses
            )

        total_credits = sum(
            section.credits * variables[section.section_id] for section in request.sections
        )
        model.add(total_credits >= request.min_credits)
        model.add(total_credits <= request.max_credits)

        for left, right in combinations(request.sections, 2):
            if left.course_id != right.course_id and sections_conflict(left, right):
                model.add(variables[left.section_id] + variables[right.section_id] <= 1)

        model.minimize(self._objective(model, variables, request, sections_by_course))
        return model, variables

    def _objective(
        self,
        model: Any,
        variables: dict[str, Any],
        request: OptimizationRequest,
        sections_by_course: dict[str, list[Section]],
    ) -> Any:
        assert cp_model is not None
        weights = request.weights
        terms: list[Any] = []
        meetings_by_day: dict[int, list[tuple[Section, Any]]] = defaultdict(list)
        for section in request.sections:
            for session in section.sessions:
                meetings_by_day[session.day].append((section, session))

        for day, meetings in meetings_by_day.items():
            day_sections = {section.section_id for section, _ in meetings}
            day_active = model.new_bool_var(f"day_{day}_active")
            model.add_max_equality(
                day_active,
                [variables[section_id] for section_id in sorted(day_sections)],
            )
            terms.append(day_active * weights.campus_day)
            if day in request.preferences.preferred_days_off:
                terms.append(day_active * weights.preferred_day_off)

            first_options: list[Any] = []
            last_options: list[Any] = []
            duration_terms: list[Any] = []
            for index, (section, session) in enumerate(meetings):
                selected = variables[section.section_id]
                first = model.new_int_var(0, 24 * 60, f"day_{day}_first_{index}")
                last = model.new_int_var(0, 24 * 60, f"day_{day}_last_{index}")
                model.add(first == session.start_minute).only_enforce_if(selected)
                model.add(first == 24 * 60).only_enforce_if(selected.Not())
                model.add(last == session.end_minute).only_enforce_if(selected)
                model.add(last == 0).only_enforce_if(selected.Not())
                first_options.append(first)
                last_options.append(last)
                duration_terms.append((session.end_minute - session.start_minute) * selected)

                if request.preferences.earliest_start_minute is not None:
                    terms.append(
                        max(
                            0,
                            request.preferences.earliest_start_minute - session.start_minute,
                        )
                        * weights.early_minute
                        * selected
                    )
                if request.preferences.latest_end_minute is not None:
                    terms.append(
                        max(
                            0,
                            session.end_minute - request.preferences.latest_end_minute,
                        )
                        * weights.late_minute
                        * selected
                    )
                if day in request.preferences.avoided_days:
                    terms.append(weights.avoided_day * selected)

            first_start = model.new_int_var(0, 24 * 60, f"day_{day}_first")
            last_end = model.new_int_var(0, 24 * 60, f"day_{day}_last")
            model.add_min_equality(first_start, first_options)
            model.add_max_equality(last_end, last_options)
            gap = model.new_int_var(0, 24 * 60, f"day_{day}_gap")
            model.add(gap == last_end - first_start - sum(duration_terms)).only_enforce_if(
                day_active
            )
            model.add(gap == 0).only_enforce_if(day_active.Not())
            terms.append(gap * weights.gap_minute)

        section_by_id = {section.section_id: section for section in request.sections}
        current_by_course = {
            section_by_id[section_id].course_id: section_id
            for section_id in request.current_section_ids
        }
        for course_id, sections in sections_by_course.items():
            current_id = current_by_course.get(course_id)
            if current_id is not None:
                terms.append((1 - variables[current_id]) * weights.section_change)
            else:
                terms.append(
                    sum(variables[section.section_id] for section in sections)
                    * weights.section_change
                )

        for section in request.sections:
            if not section.sessions:
                terms.append(variables[section.section_id] * weights.unknown_time)

        terms.extend(self._movement_terms(model, variables, request))
        return sum(terms)

    @staticmethod
    def _movement_terms(
        model: Any, variables: dict[str, Any], request: OptimizationRequest
    ) -> list[Any]:
        terms: list[Any] = []
        weight = request.weights.movement_transition
        if not weight:
            return terms
        for section in request.sections:
            transitions = sum(
                1
                for left, right in combinations(section.sessions, 2)
                if left.day == right.day
                and (
                    0 <= right.start_minute - left.end_minute <= 30
                    or 0 <= left.start_minute - right.end_minute <= 30
                )
                and left.location_group is not None
                and right.location_group is not None
                and left.location_group != right.location_group
            )
            if transitions:
                terms.append(variables[section.section_id] * transitions * weight)
        for left, right in combinations(request.sections, 2):
            transitions = sum(
                1
                for a in left.sessions
                for b in right.sessions
                if a.day == b.day
                and (
                    0 <= b.start_minute - a.end_minute <= 30
                    or 0 <= a.start_minute - b.end_minute <= 30
                )
                and a.location_group is not None
                and b.location_group is not None
                and a.location_group != b.location_group
            )
            if not transitions:
                continue
            both = model.new_bool_var(f"move_{left.section_id}_{right.section_id}")
            model.add(both <= variables[left.section_id])
            model.add(both <= variables[right.section_id])
            model.add(both >= variables[left.section_id] + variables[right.section_id] - 1)
            terms.append(both * transitions * weight)
        return terms

    @staticmethod
    def _exclude_near_duplicate(
        model: Any,
        variables: dict[str, Any],
        request: OptimizationRequest,
        selected: tuple[Section, ...],
    ) -> None:
        selected_ids = {section.section_id for section in selected}
        matching_literals = [
            variables[section.section_id]
            if section.section_id in selected_ids
            else variables[section.section_id].Not()
            for section in request.sections
        ]
        model.add(
            sum(matching_literals) <= len(request.sections) - request.minimum_candidate_difference
        )
