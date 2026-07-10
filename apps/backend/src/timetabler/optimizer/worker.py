"""Dedicated database-backed optimizer worker."""

from __future__ import annotations

import asyncio
import logging
import socket

from timetabler.api.schemas import (
    CandidateMetrics,
    OptimizationCandidate,
    OptimizationJobStatus,
    OptimizationResult,
)
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import get_settings
from timetabler.db.session import Database
from timetabler.jobs.store import OptimizationJobStore

from .cp_sat import CpSatOptimizer
from .models import OptimizationRequest, Preferences, Section, Session

LOG = logging.getLogger("timetabler.optimizer.worker")


def _to_request(job, catalog: CatalogRepository) -> OptimizationRequest:
    by_id = catalog.by_id(job.request.semester)
    sections = []
    for raw in by_id.values():
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
    selected = set(job.request.selected_section_ids)
    locked = set(job.request.locked_section_ids)
    required = frozenset(by_id[s].course_code for s in locked | selected if s in by_id)
    return OptimizationRequest(
        sections=tuple(sections),
        min_credits=round(job.request.min_credits),
        max_credits=round(job.request.max_credits),
        locked_section_ids=frozenset(locked),
        required_course_ids=required,
        max_candidates=job.request.candidate_count,
        time_limit_seconds=job.request.time_limit_seconds,
        seed=job.request.seed,
        preferences=Preferences(
            preferred_days_off=frozenset(
                "월화수목금토일".index(d) for d in job.request.preferences.preferred_days_off
            )
        ),
    )


def _to_result(result) -> tuple[OptimizationJobStatus, OptimizationResult]:
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
            ),
            score_components={"weighted": c.score.weighted_score},
            unmet_preferences=c.unmet_preferences,
        )
        for c in result.candidates
    )
    return OptimizationJobStatus(result.status.value), OptimizationResult(
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
            except Exception as exc:  # pragma: no cover - defensive process boundary
                LOG.exception("optimization job failed: %s", job.id)
                await store.fail(
                    job.id, job.lease_token, error_code="WORKER_ERROR", error_message=str(exc)
                )
    finally:
        await database.close()


def run() -> None:
    asyncio.run(run_worker())
