from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from timetabler.api.schemas import (
    CandidateMetrics,
    OptimizationCandidate,
    OptimizationCreate,
    OptimizationJobStatus,
    OptimizationResult,
)
from timetabler.db.models import OptimizationJob
from timetabler.db.session import Database
from timetabler.jobs.store import (
    ActiveJobLimitError,
    InvalidLeaseError,
    JobNotFoundError,
    OptimizationJobStore,
)


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


async def test_running_cancel_wins_completion_race_and_discards_result() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="c" * 64))
    claimed = await store.claim_next(worker_id="test-worker")
    assert claimed is not None

    cancelling = await store.cancel(created.id)
    assert cancelling.status is OptimizationJobStatus.RUNNING
    assert cancelling.cancel_requested is True

    completed = await store.complete(
        claimed.id,
        claimed.lease_token,
        status=OptimizationJobStatus.FEASIBLE,
        result=OptimizationResult(solver_version="late-result"),
    )

    assert completed.status is OptimizationJobStatus.CANCELLED
    assert completed.result is None
    assert completed.error_code is None
    assert await store.active_count() == 0
    await database.close()


async def test_active_job_cap_and_create_prunes_old_terminal_jobs() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    request = OptimizationCreate(dataset_version="d" * 64)
    first = await store.create(request, active_limit=1)
    assert await store.active_count() == 1

    try:
        await store.create(request, active_limit=1)
    except ActiveJobLimitError as exc:
        assert exc.active_count == 1
        assert exc.limit == 1
    else:
        raise AssertionError("active job cap must reject another queued job")

    await store.cancel(first.id)
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == first.id)
            .values(updated_at=datetime.now(UTC) - timedelta(hours=2))
        )

    replacement = await store.create(
        request,
        active_limit=1,
        retention=timedelta(hours=1),
    )
    assert replacement.status is OptimizationJobStatus.QUEUED
    try:
        await store.get(first.id)
    except JobNotFoundError:
        pass
    else:
        raise AssertionError("create must prune expired terminal jobs")
    await database.close()


async def test_capacity_rejection_still_commits_terminal_pruning() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    request = OptimizationCreate(dataset_version="5" * 64)
    old_terminal = await store.create(request)
    await store.cancel(old_terminal.id)
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == old_terminal.id)
            .values(updated_at=datetime.now(UTC) - timedelta(hours=2))
        )
    _active = await store.create(request)

    try:
        await store.create(request, active_limit=1, retention=timedelta(hours=1))
    except ActiveJobLimitError:
        pass
    else:
        raise AssertionError("active job cap must reject another queued job")

    try:
        await store.get(old_terminal.id)
    except JobNotFoundError:
        pass
    else:
        raise AssertionError("capacity rejection must not roll back terminal pruning")
    await database.close()


async def test_expired_running_cancel_is_swept_to_cancelled() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="e" * 64))
    claimed = await store.claim_next(worker_id="dead-worker", lease_seconds=30)
    assert claimed is not None
    await store.cancel(created.id)
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == created.id)
            .values(leased_until=datetime.now(UTC) - timedelta(seconds=1))
        )

    assert await store.claim_next(worker_id="replacement") is None
    recovered = await store.get(created.id)
    assert recovered.status is OptimizationJobStatus.CANCELLED
    assert recovered.result is None
    assert await store.active_count() == 0
    await database.close()


async def test_expired_deadline_is_swept_to_time_limit() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="f" * 64))
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == created.id)
            .values(deadline_at=datetime.now(UTC) - timedelta(seconds=1))
        )

    assert await store.claim_next(worker_id="worker") is None
    recovered = await store.get(created.id)
    assert recovered.status is OptimizationJobStatus.TIME_LIMIT
    assert recovered.result is None
    assert await store.active_count() == 0
    await database.close()


async def test_expired_max_attempt_job_fails_instead_of_consuming_capacity() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="1" * 64))
    first_claim = await store.claim_next(worker_id="dead-worker", max_attempts=1)
    assert first_claim is not None
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == created.id)
            .values(leased_until=datetime.now(UTC) - timedelta(seconds=1))
        )

    assert await store.claim_next(worker_id="replacement", max_attempts=1) is None
    recovered = await store.get(created.id)
    assert recovered.status is OptimizationJobStatus.FAILED
    assert recovered.error_code == "MAX_ATTEMPTS"
    assert await store.active_count() == 0
    await database.close()


async def test_expired_lease_is_reclaimed_before_attempt_limit() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="2" * 64))
    first_claim = await store.claim_next(worker_id="dead-worker", max_attempts=2)
    assert first_claim is not None
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == created.id)
            .values(leased_until=datetime.now(UTC) - timedelta(seconds=1))
        )

    reclaimed = await store.claim_next(worker_id="replacement", max_attempts=2)
    assert reclaimed is not None
    assert reclaimed.id == created.id
    assert reclaimed.lease_token != first_claim.lease_token
    assert (await store.get(created.id)).attempts == 2
    await database.close()


async def test_claim_renews_execution_deadline_and_get_preserves_valid_lease() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="3" * 64, time_limit_seconds=3))
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == created.id)
            .values(deadline_at=datetime.now(UTC) + timedelta(milliseconds=100))
        )

    claimed = await store.claim_next(worker_id="worker", lease_seconds=30)
    assert claimed is not None
    async with database.session_factory() as session:
        persisted = await session.get(OptimizationJob, created.id)
        assert persisted is not None
        assert persisted.deadline_at.replace(tzinfo=UTC) > datetime.now(UTC) + timedelta(seconds=25)

    # A valid lease is authoritative while the worker is solving. A stale
    # wall-clock deadline must not be able to clear it from a polling GET.
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == created.id)
            .values(deadline_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    assert (await store.get(created.id)).status is OptimizationJobStatus.RUNNING

    completed = await store.complete(
        created.id,
        claimed.lease_token,
        status=OptimizationJobStatus.FEASIBLE,
        result=OptimizationResult(solver_version="valid-lease"),
    )
    assert completed.status is OptimizationJobStatus.FEASIBLE
    await database.close()


async def test_stale_worker_result_is_rejected_after_lease_reclaim() -> None:
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_schema()
    store = OptimizationJobStore(database.session_factory)
    created = await store.create(OptimizationCreate(dataset_version="4" * 64))
    stale = await store.claim_next(worker_id="stale-worker", max_attempts=2)
    assert stale is not None
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(OptimizationJob)
            .where(OptimizationJob.id == created.id)
            .values(leased_until=datetime.now(UTC) - timedelta(seconds=1))
        )

    current = await store.claim_next(worker_id="current-worker", max_attempts=2)
    assert current is not None
    try:
        await store.complete(
            created.id,
            stale.lease_token,
            status=OptimizationJobStatus.FEASIBLE,
            result=OptimizationResult(solver_version="stale-result"),
        )
    except InvalidLeaseError:
        pass
    else:
        raise AssertionError("a stale worker must not overwrite the reclaimed attempt")

    completed = await store.complete(
        created.id,
        current.lease_token,
        status=OptimizationJobStatus.FEASIBLE,
        result=OptimizationResult(solver_version="current-result"),
    )
    assert completed.result is not None
    assert completed.result.solver_version == "current-result"
    await database.close()
