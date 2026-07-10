"""Dedicated database-backed optimizer worker."""

from __future__ import annotations

import asyncio
import logging
import socket

from timetabler.api.schemas import (
    CandidateMetrics,
    OptimizationCandidate,
    OptimizationJobStatus,
)
from timetabler.api.schemas import (
    OptimizationResult as APIOptimizationResult,
)
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import get_settings
from timetabler.db.session import Database
from timetabler.jobs.store import ClaimedJob, InvalidLeaseError, OptimizationJobStore

from .cp_sat import CpSatOptimizer
from .models import (
    Candidate,
    ObjectiveWeights,
    OptimizationRequest,
    OptimizationResult,
    Preferences,
    Section,
    Session,
)

LOG = logging.getLogger("timetabler.optimizer.worker")


def _to_request(job: ClaimedJob, catalog: CatalogRepository) -> OptimizationRequest:
    by_id = catalog.by_id(job.request.semester)
    selected = frozenset(job.request.selected_section_ids)
    locked = frozenset(job.request.locked_section_ids)
    selected_course_codes = {
        by_id[section_id].course_code for section_id in selected | locked if section_id in by_id
    }
    requested_course_codes = (
        set(job.request.required_course_codes)
        | set(job.request.candidate_course_codes)
        | selected_course_codes
    )
    # An explicit intent pool is the normal production path.  Keeping the full
    # catalog fallback preserves existing API semantics for requests that only
    # provide credit bounds.
    raw_sections = (
        (raw for raw in by_id.values() if raw.course_code in requested_course_codes)
        if requested_course_codes
        else iter(by_id.values())
    )
    sections = []
    excluded_section_ids: set[str] = set()
    excluded_course_codes = set(job.request.excluded_course_codes)
    required_course_codes = set(job.request.required_course_codes)
    for raw in raw_sections:
        if (
            not raw.sessions
            and raw.course_code not in required_course_codes
            and raw.id not in selected | locked
        ):
            # An optional TBA section would otherwise satisfy credits with zero
            # campus days and gaps. Retain it only for explicit user intent.
            continue
        sections.append(
            Section(
                section_id=raw.id,
                course_id=raw.course_code,
                credits=round(raw.credits),
                sessions=tuple(
                    Session(
                        day=("월화수목금토일".index(s.day)),
                        start_minute=s.start_minute,
                        end_minute=s.end_minute,
                        location_group=s.building_code,
                    )
                    for s in raw.sessions
                ),
            )
        )
        if raw.course_code in excluded_course_codes:
            excluded_section_ids.add(raw.id)

    required = frozenset(job.request.required_course_codes) | frozenset(
        by_id[section_id].course_code for section_id in locked if section_id in by_id
    )
    return OptimizationRequest(
        sections=tuple(sections),
        min_credits=round(job.request.min_credits),
        max_credits=round(job.request.max_credits),
        target_credits=(
            round(job.request.target_credits) if job.request.target_credits is not None else None
        ),
        locked_section_ids=locked,
        required_course_ids=required,
        current_section_ids=selected,
        excluded_section_ids=frozenset(excluded_section_ids),
        max_candidates=job.request.candidate_count,
        time_limit_seconds=job.request.time_limit_seconds,
        seed=job.request.seed,
        preferences=Preferences(
            preferred_days_off=frozenset(
                "월화수목금토일".index(d) for d in job.request.preferences.preferred_days_off
            ),
            earliest_start_minute=job.request.preferences.avoid_before_minute,
            latest_end_minute=job.request.preferences.avoid_after_minute,
            max_daily_minutes=job.request.preferences.max_daily_minutes,
            min_lunch_minutes=job.request.preferences.min_lunch_minutes,
            gap_weight_percent=(
                job.request.preferences.gap_weight_percent
                if job.request.preferences.minimize_gap_minutes
                else 0
            ),
            minimize_changes=job.request.preferences.minimize_changes,
        ),
        weights=ObjectiveWeights(
            campus_day=600 if job.request.preferences.minimize_campus_days else 0
        ),
    )


def _to_result(result: OptimizationResult) -> tuple[OptimizationJobStatus, APIOptimizationResult]:
    def explanations(c: Candidate) -> tuple[str, ...]:
        reasons = [
            f"주 {c.score.campus_days}일 등교, 수업 사이 빈 시간 {c.score.gap_minutes}분입니다.",
            "필수 과목과 잠근 분반을 모두 유지했습니다.",
        ]
        if c.score.preferred_day_off_violations == 0:
            reasons.append("선택한 공강 요일을 반영했습니다.")
        elif c.score.changed_courses == 0:
            reasons.append("현재 선택한 분반 구성을 유지했습니다.")
        else:
            reasons.append(
                f"조건을 맞추기 위해 {c.score.changed_courses}개 과목 구성을 조정했습니다."
            )
        if c.score.unknown_time_sections:
            reasons.append(
                f"시간 미정 분반 {c.score.unknown_time_sections}개는 실제 시간 충돌을 "
                "확인할 수 없습니다."
            )
        return tuple(reasons)

    candidates = tuple(
        OptimizationCandidate(
            rank=c.rank,
            section_ids=c.section_ids,
            metrics=CandidateMetrics(
                total_credits=c.total_credits,
                campus_days=c.score.campus_days,
                gap_minutes=c.score.gap_minutes,
                first_class_minute=c.score.earliest_start_minute,
                last_class_minute=c.score.latest_end_minute,
                target_credit_deviation=c.score.target_credit_deviation,
                unknown_time_sections=c.score.unknown_time_sections,
            ),
            score_components={
                "weighted": c.score.weighted_score,
                "gapMinutes": c.score.gap_minutes,
                "changedCourses": c.score.changed_courses,
                "targetCreditDeviation": c.score.target_credit_deviation,
            },
            changes=c.changed_course_ids,
            unmet_preferences=c.unmet_preferences,
            explanation=explanations(c),
        )
        for c in result.candidates
    )
    return OptimizationJobStatus(result.status.value), APIOptimizationResult(
        solver_version="ortools-cp-sat", candidates=candidates, reasons=result.relaxations
    )


async def run_worker() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    database = Database(settings.database_url)
    catalog = CatalogRepository(
        settings.data_root, validate_checksums=settings.catalog_validate_checksums
    )
    store = OptimizationJobStore(database.session_factory)
    solver = CpSatOptimizer()
    worker_id = f"{socket.gethostname()}:{id(store)}"
    try:
        await database.ping()
        LOG.info("optimizer worker ready")
        while True:
            job = await store.claim_next(worker_id=worker_id)
            if job is None:
                await asyncio.sleep(0.25)
                continue
            try:
                result = await asyncio.to_thread(solver.solve, _to_request(job, catalog))
                status, payload = _to_result(result)
                if status is OptimizationJobStatus.FAILED:
                    await store.fail(
                        job.id,
                        job.lease_token,
                        error_code="SOLVER_ERROR",
                        error_message=payload.reasons[0] if payload.reasons else "solver failed",
                    )
                else:
                    await store.complete(job.id, job.lease_token, status=status, result=payload)
            except InvalidLeaseError:
                # Another worker reclaimed the expired lease (or a recovery
                # sweep made the job terminal). Its state is authoritative;
                # discard this stale result without terminating the process.
                LOG.info("discarding stale optimization result: %s", job.id)
            except Exception as exc:  # pragma: no cover - defensive process boundary
                LOG.exception("optimization job failed: %s", job.id)
                try:
                    await store.fail(
                        job.id, job.lease_token, error_code="WORKER_ERROR", error_message=str(exc)
                    )
                except InvalidLeaseError:
                    LOG.info("discarding stale optimization failure: %s", job.id)
    finally:
        await database.close()


def run() -> None:
    asyncio.run(run_worker())
