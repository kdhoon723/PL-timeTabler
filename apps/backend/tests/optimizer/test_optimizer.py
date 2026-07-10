from __future__ import annotations

import random
import unittest

from timetabler.optimizer import (
    BacktrackingOptimizer,
    CpSatOptimizer,
    OptimizationRequest,
    Preferences,
    RequiredGroup,
    Section,
    Session,
    SolverStatus,
)
from timetabler.optimizer.constraints import selection_is_feasible, sessions_overlap
from timetabler.optimizer.scoring import build_candidate


def section(
    section_id: str,
    course_id: str,
    credits: int,
    *sessions: Session,
    verified_eligible: bool | None = None,
) -> Section:
    return Section(
        section_id=section_id,
        course_id=course_id,
        credits=credits,
        sessions=tuple(sessions),
        verified_eligible=verified_eligible,
    )


class IntervalAndScoringTests(unittest.TestCase):
    def test_adjacent_half_open_intervals_do_not_conflict(self) -> None:
        first = Session(0, 9 * 60, 10 * 60)
        adjacent = Session(0, 10 * 60, 11 * 60)
        overlapping = Session(0, 9 * 60 + 59, 11 * 60)

        self.assertFalse(sessions_overlap(first, adjacent))
        self.assertTrue(sessions_overlap(first, overlapping))

    def test_score_exposes_gaps_changes_preferences_unknown_times_and_movement(
        self,
    ) -> None:
        a = section("A-1", "A", 3, Session(0, 8 * 60, 9 * 60, "north"))
        b = section("B-1", "B", 3, Session(0, 9 * 60 + 20, 10 * 60, "south"))
        unknown = section("C-1", "C", 1)
        request = OptimizationRequest(
            sections=(a, b, unknown),
            current_section_ids=frozenset({"A-1"}),
            preferences=Preferences(
                preferred_days_off=frozenset({0}),
                avoided_days=frozenset({0}),
                earliest_start_minute=9 * 60,
                latest_end_minute=9 * 60 + 30,
                max_campus_days=0,
            ),
        )

        candidate = build_candidate(request, (a, b, unknown), rank=1)

        self.assertEqual(candidate.score.campus_days, 1)
        self.assertEqual(candidate.score.gap_minutes, 20)
        self.assertEqual(candidate.score.early_minutes, 60)
        self.assertEqual(candidate.score.late_minutes, 30)
        self.assertEqual(candidate.score.preferred_day_off_violations, 1)
        self.assertEqual(candidate.score.avoided_day_sessions, 2)
        self.assertEqual(candidate.score.changed_courses, 2)
        self.assertEqual(candidate.score.unknown_time_sections, 1)
        self.assertEqual(candidate.score.movement_transitions, 1)
        self.assertTrue(candidate.unmet_preferences)


class BacktrackingOptimizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a1 = section("A-1", "A", 3, Session(0, 9 * 60, 10 * 60))
        self.a2 = section("A-2", "A", 3, Session(1, 9 * 60, 10 * 60))
        self.b1 = section("B-1", "B", 3, Session(0, 9 * 60 + 30, 10 * 60 + 30))
        self.b2 = section("B-2", "B", 3, Session(0, 10 * 60, 11 * 60))
        self.c1 = section("C-1", "C", 2, Session(2, 9 * 60, 10 * 60))

    def test_hard_constraints_and_diverse_candidates(self) -> None:
        request = OptimizationRequest(
            sections=(self.a1, self.a2, self.b1, self.b2, self.c1),
            min_credits=6,
            max_credits=6,
            locked_section_ids=frozenset({"A-1"}),
            required_course_ids=frozenset({"B"}),
            max_candidates=3,
        )

        result = BacktrackingOptimizer().solve(request)

        self.assertEqual(result.status, SolverStatus.OPTIMAL)
        self.assertGreaterEqual(len(result.candidates), 1)
        self.assertEqual(result.candidates[0].section_ids, ("A-1", "B-2"))
        for candidate in result.candidates:
            selected = tuple(
                item
                for item in request.sections
                if item.section_id in candidate.section_ids
            )
            self.assertTrue(selection_is_feasible(request, selected))
        self.assertEqual(
            len({candidate.section_ids for candidate in result.candidates}),
            len(result.candidates),
        )

    def test_required_group_and_unverified_restriction(self) -> None:
        unverified = section(
            "D-1", "D", 3, Session(3, 9 * 60, 10 * 60), verified_eligible=None
        )
        request = OptimizationRequest(
            sections=(self.a1, self.c1, unverified),
            min_credits=5,
            max_credits=6,
            required_groups=(RequiredGroup("major", frozenset({"C", "D"}), 1),),
            required_course_ids=frozenset({"A"}),
        )

        result = BacktrackingOptimizer().solve(request)

        self.assertEqual(result.status, SolverStatus.OPTIMAL)
        self.assertTrue(
            any("D-1" in candidate.section_ids for candidate in result.candidates)
        )

    def test_verified_ineligible_section_is_excluded(self) -> None:
        unavailable = section(
            "D-1", "D", 3, Session(3, 9 * 60, 10 * 60), verified_eligible=False
        )
        request = OptimizationRequest(
            sections=(unavailable,),
            min_credits=3,
            required_course_ids=frozenset({"D"}),
        )

        result = BacktrackingOptimizer().solve(request)

        self.assertEqual(result.status, SolverStatus.INFEASIBLE)
        self.assertTrue(result.relaxations)

    def test_conflicting_locks_are_infeasible_with_relaxation(self) -> None:
        request = OptimizationRequest(
            sections=(self.a1, self.b1),
            locked_section_ids=frozenset({"A-1", "B-1"}),
            min_credits=6,
            max_credits=6,
        )

        result = BacktrackingOptimizer().solve(request)

        self.assertEqual(result.status, SolverStatus.INFEASIBLE)
        self.assertIn("잠금", " ".join(result.relaxations))

    def test_malformed_duplicate_ids_fail_without_throwing(self) -> None:
        duplicate = section("A-1", "OTHER", 1, Session(2, 12 * 60, 13 * 60))
        request = OptimizationRequest(sections=(self.a1, duplicate))

        result = BacktrackingOptimizer().solve(request)

        self.assertEqual(result.status, SolverStatus.FAILED)
        self.assertIn("duplicate", result.error or "")

    def test_multiple_current_sections_for_one_course_fail_validation(self) -> None:
        request = OptimizationRequest(
            sections=(self.a1, self.a2),
            current_section_ids=frozenset({"A-1", "A-2"}),
        )

        result = BacktrackingOptimizer().solve(request)

        self.assertEqual(result.status, SolverStatus.FAILED)
        self.assertIn("multiple current", result.error or "")


@unittest.skipUnless(
    CpSatOptimizer().solve(OptimizationRequest(sections=())).error is None,
    "OR-Tools not installed",
)
class CpSatOptimizerTests(unittest.TestCase):
    def test_cp_sat_is_deterministic_and_returns_distinct_candidates(self) -> None:
        sections = tuple(
            section(
                f"{course}-{variant}",
                course,
                3,
                Session(variant, 9 * 60 + index * 60, 10 * 60 + index * 60),
            )
            for index, course in enumerate(("A", "B", "C"))
            for variant in (0, 1)
        )
        request = OptimizationRequest(
            sections=sections,
            min_credits=6,
            max_credits=6,
            max_candidates=3,
            seed=47,
        )

        first = CpSatOptimizer().solve(request)
        second = CpSatOptimizer().solve(request)

        self.assertIn(first.status, {SolverStatus.OPTIMAL, SolverStatus.FEASIBLE})
        self.assertEqual(
            [candidate.section_ids for candidate in first.candidates],
            [candidate.section_ids for candidate in second.candidates],
        )
        self.assertEqual(len(first.candidates), 3)
        self.assertEqual(
            len({candidate.section_ids for candidate in first.candidates}), 3
        )

    def test_cp_sat_distinguishes_infeasible(self) -> None:
        a = section("A-1", "A", 3, Session(0, 9 * 60, 10 * 60))
        b = section("B-1", "B", 3, Session(0, 9 * 60 + 30, 10 * 60 + 30))
        request = OptimizationRequest(
            sections=(a, b),
            locked_section_ids=frozenset({"A-1", "B-1"}),
            min_credits=6,
        )

        result = CpSatOptimizer().solve(request)

        self.assertEqual(result.status, SolverStatus.INFEASIBLE)
        self.assertTrue(result.relaxations)

    def test_fifty_small_fixtures_match_reference_feasibility(self) -> None:
        """Operational-gate baseline: 50 normal/boundary/infeasible fixtures."""

        cp_sat = CpSatOptimizer()
        reference = BacktrackingOptimizer()
        for seed in range(50):
            rng = random.Random(seed)
            sections: list[Section] = []
            for course_index in range(4):
                course = chr(ord("A") + course_index)
                for variant in range(2):
                    day = rng.randrange(3)
                    start = (8 + rng.randrange(5)) * 60
                    sections.append(
                        section(
                            f"{course}-{variant}",
                            course,
                            rng.choice((1, 2, 3)),
                            Session(day, start, start + rng.choice((50, 60, 90))),
                        )
                    )
            request = OptimizationRequest(
                sections=tuple(sections),
                min_credits=rng.randrange(2, 7),
                max_credits=rng.randrange(7, 11),
                required_course_ids=frozenset({"A"}) if seed % 3 == 0 else frozenset(),
                locked_section_ids=frozenset({"B-0"}) if seed % 7 == 0 else frozenset(),
                max_candidates=1,
                seed=seed,
            )

            cp_result = cp_sat.solve(request)
            reference_result = reference.solve(request)

            self.assertEqual(
                bool(cp_result.candidates),
                bool(reference_result.candidates),
                f"feasibility mismatch for fixture seed={seed}",
            )
            for candidate in cp_result.candidates:
                selected = tuple(
                    item
                    for item in request.sections
                    if item.section_id in candidate.section_ids
                )
                self.assertTrue(
                    selection_is_feasible(request, selected), f"invalid seed={seed}"
                )


if __name__ == "__main__":
    unittest.main()
