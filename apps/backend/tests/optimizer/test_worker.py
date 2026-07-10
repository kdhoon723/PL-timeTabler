from __future__ import annotations

from timetabler.api.schemas import OptimizationCreate, OptimizationPreferences
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import repository_root
from timetabler.jobs.store import ClaimedJob
from timetabler.optimizer import CpSatOptimizer, SolverStatus
from timetabler.optimizer.constraints import selection_is_feasible
from timetabler.optimizer.worker import _to_request, _to_result


def claimed_job(request: OptimizationCreate) -> ClaimedJob:
    return ClaimedJob(
        id="optimizer-regression",
        lease_token="lease-token",
        request=request,
        cancel_requested=False,
    )


def test_worker_maps_course_intent_and_hard_constraints() -> None:
    catalog = CatalogRepository(repository_root() / "data")
    request = OptimizationCreate(
        dataset_version=catalog.snapshot.dataset_version,
        required_course_codes=("005111",),
        candidate_course_codes=("927283",),
        excluded_course_codes=("927430",),
        locked_section_ids=("005111-01",),
        selected_section_ids=("005111-01", "927283-01", "927430-01"),
        min_credits=5,
        max_credits=7,
        target_credits=6,
        preferences=OptimizationPreferences(
            preferred_days_off=("금",),
            avoid_before_minute=600,
            avoid_after_minute=1020,
            max_daily_minutes=300,
            min_lunch_minutes=60,
            gap_weight_percent=80,
            minimize_changes=False,
        ),
    )

    normalized = _to_request(claimed_job(request), catalog)

    assert {section.course_id for section in normalized.sections} == {
        "005111",
        "927283",
        "927430",
    }
    assert normalized.required_course_ids == frozenset({"005111"})
    assert normalized.locked_section_ids == frozenset({"005111-01"})
    assert normalized.current_section_ids == frozenset(request.selected_section_ids)
    assert normalized.excluded_section_ids == frozenset(
        section.section_id for section in normalized.sections if section.course_id == "927430"
    )
    assert normalized.preferences.preferred_days_off == frozenset({4})
    assert normalized.preferences.earliest_start_minute == 600
    assert normalized.preferences.latest_end_minute == 1020
    assert normalized.preferences.max_daily_minutes == 300
    assert normalized.preferences.min_lunch_minutes == 60
    assert normalized.preferences.gap_weight_percent == 80
    assert normalized.preferences.minimize_changes is False
    assert normalized.target_credits == 6

    result = CpSatOptimizer().solve(normalized)

    assert result.status in {SolverStatus.OPTIMAL, SolverStatus.FEASIBLE}
    assert result.candidates
    for candidate in result.candidates:
        selected = tuple(
            section
            for section in normalized.sections
            if section.section_id in candidate.section_ids
        )
        assert selection_is_feasible(normalized, selected)


def test_production_catalog_is_pruned_and_returns_deterministic_candidates() -> None:
    """Regression for the 1,576-section TIME_LIMIT-without-candidate failure."""

    catalog = CatalogRepository(repository_root() / "data")
    assert len(catalog.snapshot.sections) == 1576
    request = OptimizationCreate(
        dataset_version=catalog.snapshot.dataset_version,
        candidate_course_codes=("927283", "927430", "922601", "005111", "005005"),
        selected_section_ids=(
            "927283-01",
            "927430-01",
            "922601-01",
            "005111-01",
            "005005-01",
        ),
        min_credits=9,
        max_credits=12,
        candidate_count=3,
        time_limit_seconds=3,
        seed=47,
    )

    normalized = _to_request(claimed_job(request), catalog)
    first = CpSatOptimizer().solve(normalized)
    second = CpSatOptimizer().solve(normalized)

    assert len(normalized.sections) == 89
    assert first.status is SolverStatus.OPTIMAL
    assert len(first.candidates) == request.candidate_count
    assert first.wall_time_seconds < request.time_limit_seconds
    assert [candidate.section_ids for candidate in first.candidates] == [
        candidate.section_ids for candidate in second.candidates
    ]


def test_full_production_pool_returns_a_feasible_time_limit_fallback() -> None:
    """Even an unscoped legacy job must not finish TIME_LIMIT with no candidate."""

    catalog = CatalogRepository(repository_root() / "data")
    request = OptimizationCreate(
        dataset_version=catalog.snapshot.dataset_version,
        min_credits=12,
        max_credits=18,
        candidate_count=1,
        time_limit_seconds=3,
    )
    normalized = _to_request(claimed_job(request), catalog)

    result = CpSatOptimizer().solve(normalized)

    assert len(normalized.sections) == sum(
        bool(section.sessions) for section in catalog.snapshot.sections
    )
    assert result.status in {
        SolverStatus.OPTIMAL,
        SolverStatus.FEASIBLE,
        SolverStatus.TIME_LIMIT,
    }
    assert len(result.candidates) == 1
    selected = tuple(
        section
        for section in normalized.sections
        if section.section_id in result.candidates[0].section_ids
    )
    assert selection_is_feasible(normalized, selected)


def test_optional_tba_field_practice_cannot_dominate_automatic_candidates() -> None:
    catalog = CatalogRepository(repository_root() / "data")
    request = OptimizationCreate(
        dataset_version=catalog.snapshot.dataset_version,
        candidate_course_codes=(
            "956004",
            "927283",
            "927430",
            "922601",
            "005111",
            "005005",
        ),
        min_credits=12,
        max_credits=18,
        target_credits=12,
        candidate_count=1,
        time_limit_seconds=3,
        seed=2996,
    )

    normalized = _to_request(claimed_job(request), catalog)
    result = CpSatOptimizer().solve(normalized)

    assert "956004-01" not in {section.section_id for section in normalized.sections}
    assert result.candidates
    assert result.candidates[0].section_ids != ("956004-01",)
    assert "956004-01" not in result.candidates[0].section_ids


def test_locked_tba_section_remains_feasible_with_explicit_warning() -> None:
    catalog = CatalogRepository(repository_root() / "data")
    request = OptimizationCreate(
        dataset_version=catalog.snapshot.dataset_version,
        locked_section_ids=("956004-01",),
        selected_section_ids=("956004-01",),
        min_credits=12,
        max_credits=12,
        target_credits=12,
        candidate_count=1,
        time_limit_seconds=3,
    )

    normalized = _to_request(claimed_job(request), catalog)
    result = CpSatOptimizer().solve(normalized)
    _, api_result = _to_result(result)

    assert result.candidates
    assert result.candidates[0].section_ids == ("956004-01",)
    assert result.candidates[0].score.unknown_time_sections == 1
    assert "시간 미정" in " ".join(result.candidates[0].unmet_preferences)
    assert "시간 미정" in " ".join(api_result.candidates[0].explanation)
