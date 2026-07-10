"""Deterministic production CP-SAT timetable optimizer."""

from __future__ import annotations

from collections import defaultdict
from time import monotonic
from typing import Any

from .constraints import infeasibility_hints, validate_request
from .models import (
    Candidate,
    OptimizationRequest,
    OptimizationResult,
    Section,
    SolverStatus,
)
from .scoring import (
    LUNCH_END_MINUTE,
    LUNCH_START_MINUTE,
    PREFERENCE_PERCENT_BASE,
    build_candidate,
)

try:
    from ortools.sat.python import cp_model
except ImportError:  # pragma: no cover - exercised only before backend dependencies install
    cp_model = None  # type: ignore[assignment]


class CpSatOptimizer:
    """Build and solve the production integer model without transport side effects."""

    _LARGE_PROBLEM_SECTION_COUNT = 250
    _FEASIBILITY_BUDGET_SECONDS = 0.5

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

        fallback, feasibility_branches = self._large_problem_fallback(request, started)
        model, variables = self._build_model(request)
        if fallback is not None:
            selected_ids = set(fallback.section_ids)
            for section_id, variable in variables.items():
                model.add_hint(variable, section_id in selected_ids)
        candidates: list[Candidate] = []
        overall_status = SolverStatus.OPTIMAL
        explored_branches = feasibility_branches

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

        if not candidates and fallback is not None and overall_status is SolverStatus.TIME_LIMIT:
            candidates.append(fallback)

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

    def _large_problem_fallback(
        self, request: OptimizationRequest, started: float
    ) -> tuple[Candidate | None, int]:
        """Reserve a small budget for a hard-feasible fallback on large pools.

        CP-SAT may spend an entire short deadline presolving a large optimization
        objective without publishing an incumbent.  A compact feasibility pass
        uses the exact same hard constraints and ensures that a feasible timetable
        can still be returned with ``TIME_LIMIT`` rather than an empty result.
        """

        assert cp_model is not None
        if len(request.sections) < self._LARGE_PROBLEM_SECTION_COUNT:
            return None, 0
        remaining = request.time_limit_seconds - (monotonic() - started)
        budget = min(self._FEASIBILITY_BUDGET_SECONDS, remaining / 3)
        if budget <= 0:
            return None, 0

        model, variables = self._build_model(request, include_objective=False)
        remaining = request.time_limit_seconds - (monotonic() - started)
        if remaining <= 0:
            return None, 0

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = min(budget, remaining)
        solver.parameters.random_seed = request.seed
        solver.parameters.num_search_workers = 1
        # This stage needs the first hard-feasible incumbent, not a proof.  On the
        # 1,576-section catalog, full presolve costs more than direct propagation.
        solver.parameters.cp_model_presolve = False
        status = solver.solve(model)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return None, solver.num_branches
        selected = tuple(
            section
            for section in request.sections
            if solver.boolean_value(variables[section.section_id])
        )
        return build_candidate(request, selected, rank=1), solver.num_branches

    def _build_model(
        self, request: OptimizationRequest, *, include_objective: bool = True
    ) -> tuple[Any, dict[str, Any]]:
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

        intervals_by_day: dict[int, list[Any]] = defaultdict(list)
        for section in request.sections:
            selected = variables[section.section_id]
            for index, session in enumerate(section.sessions):
                intervals_by_day[session.day].append(
                    model.new_optional_fixed_size_interval_var(
                        session.start_minute,
                        session.end_minute - session.start_minute,
                        selected,
                        f"meeting_{section.section_id}_{index}",
                    )
                )
        for intervals in intervals_by_day.values():
            model.add_no_overlap(intervals)

        if include_objective:
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
            terms.append(day_active * weights.campus_day * PREFERENCE_PERCENT_BASE)
            if day in request.preferences.preferred_days_off:
                terms.append(day_active * weights.preferred_day_off * PREFERENCE_PERCENT_BASE)

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
                        * PREFERENCE_PERCENT_BASE
                        * selected
                    )
                if request.preferences.latest_end_minute is not None:
                    terms.append(
                        max(
                            0,
                            session.end_minute - request.preferences.latest_end_minute,
                        )
                        * weights.late_minute
                        * PREFERENCE_PERCENT_BASE
                        * selected
                    )
                if day in request.preferences.avoided_days:
                    terms.append(weights.avoided_day * PREFERENCE_PERCENT_BASE * selected)

            first_start = model.new_int_var(0, 24 * 60, f"day_{day}_first")
            last_end = model.new_int_var(0, 24 * 60, f"day_{day}_last")
            model.add_min_equality(first_start, first_options)
            model.add_max_equality(last_end, last_options)
            gap = model.new_int_var(0, 24 * 60, f"day_{day}_gap")
            model.add(gap == last_end - first_start - sum(duration_terms)).only_enforce_if(
                day_active
            )
            model.add(gap == 0).only_enforce_if(day_active.Not())
            terms.append(gap * weights.gap_minute * request.preferences.gap_weight_percent)

            if request.preferences.max_daily_minutes is not None:
                daily_overflow = model.new_int_var(0, 24 * 60, f"day_{day}_overflow")
                model.add_max_equality(
                    daily_overflow,
                    [sum(duration_terms) - request.preferences.max_daily_minutes, 0],
                )
                terms.append(
                    daily_overflow * weights.daily_overflow_minute * PREFERENCE_PERCENT_BASE
                )

            if request.preferences.min_lunch_minutes:
                lunch_shortage = self._lunch_shortage(
                    model,
                    variables,
                    meetings,
                    day=day,
                    requested_minutes=request.preferences.min_lunch_minutes,
                )
                terms.append(
                    lunch_shortage * weights.lunch_shortage_minute * PREFERENCE_PERCENT_BASE
                )

        section_by_id = {section.section_id: section for section in request.sections}
        current_by_course = {
            section_by_id[section_id].course_id: section_id
            for section_id in request.current_section_ids
        }
        if request.preferences.minimize_changes:
            for course_id, sections in sections_by_course.items():
                current_id = current_by_course.get(course_id)
                if current_id is not None:
                    terms.append(
                        (1 - variables[current_id])
                        * weights.section_change
                        * PREFERENCE_PERCENT_BASE
                    )
                else:
                    terms.append(
                        sum(variables[section.section_id] for section in sections)
                        * weights.section_change
                        * PREFERENCE_PERCENT_BASE
                    )

        for section in request.sections:
            if not section.sessions:
                terms.append(
                    variables[section.section_id] * weights.unknown_time * PREFERENCE_PERCENT_BASE
                )

        if request.target_credits is not None:
            total_credits = sum(
                section.credits * variables[section.section_id] for section in request.sections
            )
            credit_deviation = model.new_int_var(0, request.max_credits, "credit_deviation")
            model.add_abs_equality(credit_deviation, total_credits - request.target_credits)
            terms.append(credit_deviation * weights.target_credit * PREFERENCE_PERCENT_BASE)

        terms.extend(
            term * PREFERENCE_PERCENT_BASE
            for term in self._movement_terms(model, variables, request)
        )
        return sum(terms)

    @staticmethod
    def _lunch_shortage(
        model: Any,
        variables: dict[str, Any],
        meetings: list[tuple[Section, Any]],
        *,
        day: int,
        requested_minutes: int,
    ) -> Any:
        """Model shortage against the longest continuous lunch-window gap."""

        section_ids_by_event: dict[tuple[int, int], set[str]] = defaultdict(set)
        for section, session in meetings:
            occupied_start = max(session.start_minute, LUNCH_START_MINUTE)
            occupied_end = min(session.end_minute, LUNCH_END_MINUTE)
            if occupied_start < occupied_end:
                section_ids_by_event[(occupied_start, occupied_end)].add(section.section_id)

        events: list[tuple[int, int, Any]] = []
        for index, ((start, end), section_ids) in enumerate(sorted(section_ids_by_event.items())):
            active = model.new_bool_var(f"day_{day}_lunch_event_{index}")
            model.add(active == sum(variables[section_id] for section_id in sorted(section_ids)))
            events.append((start, end, active))

        if not events:
            return 0

        gap_candidates: list[Any] = []
        no_event = model.new_bool_var(f"day_{day}_lunch_no_event")
        active_count = sum(event[2] for event in events)
        model.add(active_count == 0).only_enforce_if(no_event)
        model.add(active_count >= 1).only_enforce_if(no_event.Not())
        gap_candidates.append((LUNCH_END_MINUTE - LUNCH_START_MINUTE) * no_event)

        for index, (start, end, active) in enumerate(events):
            earlier = [event[2] for event in events[:index]]
            is_first = model.new_bool_var(f"day_{day}_lunch_first_{index}")
            model.add(is_first <= active)
            for earlier_active in earlier:
                model.add(is_first + earlier_active <= 1)
            model.add(is_first >= active - sum(earlier))
            gap_candidates.append((start - LUNCH_START_MINUTE) * is_first)

            later = [event[2] for event in events[index + 1 :]]
            is_last = model.new_bool_var(f"day_{day}_lunch_last_{index}")
            model.add(is_last <= active)
            for later_active in later:
                model.add(is_last + later_active <= 1)
            model.add(is_last >= active - sum(later))
            gap_candidates.append((LUNCH_END_MINUTE - end) * is_last)

            for right_index in range(index + 1, len(events)):
                right_start, _, right_active = events[right_index]
                gap = right_start - end
                if gap <= 0:
                    continue
                intermediates = [event[2] for event in events[index + 1 : right_index]]
                adjacent = model.new_bool_var(f"day_{day}_lunch_adjacent_{index}_{right_index}")
                model.add(adjacent <= active)
                model.add(adjacent <= right_active)
                for intermediate in intermediates:
                    model.add(adjacent + intermediate <= 1)
                model.add(adjacent >= active + right_active - 1 - sum(intermediates))
                gap_candidates.append(gap * adjacent)

        longest_break = model.new_int_var(
            0,
            LUNCH_END_MINUTE - LUNCH_START_MINUTE,
            f"day_{day}_longest_lunch_break",
        )
        model.add_max_equality(longest_break, gap_candidates)
        shortage = model.new_int_var(0, requested_minutes, f"day_{day}_lunch_shortage")
        model.add_max_equality(shortage, [requested_minutes - longest_break, 0])
        return shortage

    @staticmethod
    def _movement_terms(
        model: Any, variables: dict[str, Any], request: OptimizationRequest
    ) -> list[Any]:
        """Count movement only between chronologically adjacent selected sessions.

        The public scorer sorts all selected sessions and uses ``pairwise``. A
        pairwise cost over every near event over-counts A→C when B is selected
        between them. The adjacency literal below is true exactly when both end
        events are selected and every chronologically intermediate event is not.
        Events with unknown locations are retained as intermediates even though
        they never incur movement cost themselves.
        """

        terms: list[Any] = []
        weight = request.weights.movement_transition
        if not weight:
            return terms

        sections_by_event: dict[tuple[int, int, int, str | None], set[str]] = defaultdict(set)
        for section in request.sections:
            for session in section.sessions:
                sections_by_event[
                    (
                        session.day,
                        session.start_minute,
                        session.end_minute,
                        session.location_group,
                    )
                ].add(section.section_id)

        ordered_events = sorted(
            sections_by_event.items(),
            key=lambda item: (
                item[0][0],
                item[0][1],
                item[0][2],
                item[0][3] or "",
            ),
        )
        event_active: dict[tuple[int, int, int, str | None], Any] = {}
        for index, (event, section_ids) in enumerate(ordered_events):
            active = model.new_bool_var(f"move_event_{index}")
            model.add(active == sum(variables[section_id] for section_id in sorted(section_ids)))
            event_active[event] = active

        events_by_day: dict[int, list[tuple[int, int, str | None, Any]]] = defaultdict(list)
        for (day, start, end, location), active in event_active.items():
            events_by_day[day].append((start, end, location, active))

        transition_index = 0
        for events in events_by_day.values():
            events.sort(key=lambda event: (event[0], event[1], event[2] or ""))
            for left_index, left in enumerate(events):
                for right_index in range(left_index + 1, len(events)):
                    right = events[right_index]
                    gap = right[0] - left[1]
                    if gap < 0 or gap > 30:
                        continue
                    if left[2] is None or right[2] is None or left[2] == right[2]:
                        continue
                    intermediates = [event[3] for event in events[left_index + 1 : right_index]]
                    adjacent = model.new_bool_var(f"move_transition_{transition_index}")
                    transition_index += 1
                    model.add(adjacent <= left[3])
                    model.add(adjacent <= right[3])
                    for intermediate in intermediates:
                        model.add(adjacent + intermediate <= 1)
                    model.add(adjacent >= left[3] + right[3] - 1 - sum(intermediates))
                    terms.append(adjacent * weight)
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
