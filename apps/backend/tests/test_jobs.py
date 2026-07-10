from __future__ import annotations

from timetabler.api.schemas import (
    CandidateMetrics,
    OptimizationCandidate,
    OptimizationCreate,
    OptimizationJobStatus,
    OptimizationResult,
)
from timetabler.db.session import Database
from timetabler.jobs.store import InvalidLeaseError, OptimizationJobStore


async def test_job_claim_complete_and_lease_enforcement(tmp_path: object) -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    request = OptimizationCreate(dataset_version="a" * 64)
    created = await store.create(request)

    claimed = await store.claim_next(worker_id="test-worker")
    assert claimed is not None
    assert claimed.id == created.id
    assert await store.claim_next(worker_id="other-worker") is None

    result = OptimizationResult(
        solver_version="test",
        candidates=(
            OptimizationCandidate(
                rank=1,
                section_ids=("922601-01",),
                metrics=CandidateMetrics(
                    total_credits=2,
                    campus_days=1,
                    gap_minutes=0,
                    first_class_minute=690,
                    last_class_minute=810,
                ),
                score_components={"campusDays": 1},
            ),
        ),
    )
    completed = await store.complete(
        claimed.id,
        claimed.lease_token,
        status=OptimizationJobStatus.FEASIBLE,
        result=result,
    )
    assert completed.status is OptimizationJobStatus.FEASIBLE
    assert completed.result == result

    try:
        await store.heartbeat(claimed.id, claimed.lease_token)
    except InvalidLeaseError:
        pass
    else:
        raise AssertionError("completed lease must not remain valid")
    await database.close()


async def test_queued_cancel_is_idempotent() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="b" * 64))

    first = await store.cancel(created.id)
    second = await store.cancel(created.id)

    assert first.status is OptimizationJobStatus.CANCELLED
    assert second.status is OptimizationJobStatus.CANCELLED
    assert await store.claim_next(worker_id="test-worker") is None
    await database.close()
