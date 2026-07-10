from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Select, delete, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from timetabler.api.schemas import (
    OptimizationCreate,
    OptimizationJobRead,
    OptimizationJobStatus,
    OptimizationResult,
)
from timetabler.db.models import OptimizationJob


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: str
    lease_token: str
    request: OptimizationCreate
    cancel_requested: bool


class JobNotFoundError(LookupError):
    pass


class InvalidLeaseError(RuntimeError):
    pass


class ActiveJobLimitError(RuntimeError):
    def __init__(self, active_count: int, limit: int, *, retry_after_seconds: int = 5) -> None:
        super().__init__(f"active optimization job limit reached: {active_count}/{limit}")
        self.active_count = active_count
        self.limit = limit
        self.retry_after_seconds = retry_after_seconds


ACTIVE_STATUSES = (
    OptimizationJobStatus.QUEUED,
    OptimizationJobStatus.RUNNING,
)
TERMINAL_STATUSES = (
    OptimizationJobStatus.OPTIMAL,
    OptimizationJobStatus.FEASIBLE,
    OptimizationJobStatus.INFEASIBLE,
    OptimizationJobStatus.TIME_LIMIT,
    OptimizationJobStatus.FAILED,
    OptimizationJobStatus.CANCELLED,
)
_ADMISSION_LOCK_ID = 6_240_257_716_629_087_121


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class OptimizationJobStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        request: OptimizationCreate,
        *,
        active_limit: int = 100,
        retention: timedelta = timedelta(hours=24),
    ) -> OptimizationJobRead:
        if active_limit < 1:
            raise ValueError("active_limit must be positive")
        if retention.total_seconds() <= 0:
            raise ValueError("retention must be positive")
        now = datetime.now(UTC)
        job = OptimizationJob(
            id=str(uuid4()),
            status=OptimizationJobStatus.QUEUED,
            input_snapshot=request.model_dump(mode="json", by_alias=True),
            result_snapshot=None,
            attempts=0,
            cancel_requested=False,
            deadline_at=now + timedelta(seconds=request.time_limit_seconds + 30),
            created_at=now,
            updated_at=now,
        )
        capacity_error: ActiveJobLimitError | None = None
        async with self._session_factory() as session, session.begin():
            if session.get_bind().dialect.name == "postgresql":
                # Count-and-insert must be serialized across API workers. The
                # in-memory limiter is deliberately only a per-process first line.
                await session.execute(
                    text("SELECT pg_advisory_xact_lock(:lock_id)"),
                    {"lock_id": _ADMISSION_LOCK_ID},
                )
            await self._sweep_active(session, now=now, max_attempts=3)
            await self._prune_terminal(session, older_than=now - retention)
            active_count = await self._active_count(session)
            if active_count >= active_limit:
                capacity_error = ActiveJobLimitError(active_count, active_limit)
            else:
                session.add(job)
        if capacity_error is not None:
            # Raise after the maintenance transaction commits. Otherwise a full
            # queue would roll back the sweep/prune that makes future capacity.
            raise capacity_error
        return self._to_read(job)

    async def active_count(self) -> int:
        async with self._session_factory() as session:
            return await self._active_count(session)

    async def prune_terminal(self, *, older_than: datetime) -> int:
        async with self._session_factory() as session, session.begin():
            return await self._prune_terminal(session, older_than=older_than)

    async def get(self, job_id: str) -> OptimizationJobRead:
        async with self._session_factory() as session, session.begin():
            await self._sweep_active(session, now=datetime.now(UTC), max_attempts=3)
            job = await session.get(OptimizationJob, job_id)
            if job is None:
                raise JobNotFoundError(job_id)
            return self._to_read(job)

    async def cancel(self, job_id: str) -> OptimizationJobRead:
        async with self._session_factory() as session, session.begin():
            job = await session.get(OptimizationJob, job_id, with_for_update=True)
            if job is None:
                raise JobNotFoundError(job_id)
            status = OptimizationJobStatus(job.status)
            if status is OptimizationJobStatus.QUEUED:
                job.status = OptimizationJobStatus.CANCELLED
            elif status is OptimizationJobStatus.RUNNING:
                job.cancel_requested = True
            job.updated_at = datetime.now(UTC)
        return self._to_read(job)

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_seconds: int = 30,
        max_attempts: int = 3,
    ) -> ClaimedJob | None:
        now = datetime.now(UTC)
        claimable: Select[tuple[OptimizationJob]] = (
            select(OptimizationJob)
            .where(
                OptimizationJob.cancel_requested.is_(False),
                OptimizationJob.attempts < max_attempts,
                OptimizationJob.deadline_at > now,
                or_(
                    OptimizationJob.status == OptimizationJobStatus.QUEUED,
                    (
                        (OptimizationJob.status == OptimizationJobStatus.RUNNING)
                        & or_(
                            OptimizationJob.leased_until.is_(None),
                            OptimizationJob.leased_until < now,
                        )
                    ),
                ),
            )
            .order_by(OptimizationJob.created_at, OptimizationJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        async with self._session_factory() as session, session.begin():
            await self._sweep_active(session, now=now, max_attempts=max_attempts)
            job = (await session.execute(claimable)).scalar_one_or_none()
            if job is None:
                return None
            request = OptimizationCreate.model_validate(job.input_snapshot)
            lease_token = str(uuid4())
            job.status = OptimizationJobStatus.RUNNING
            job.lease_token = lease_token
            job.worker_id = worker_id
            job.leased_until = now + timedelta(seconds=lease_seconds)
            # Queue admission has a bounded wait deadline. Once work is claimed,
            # give this concrete attempt its own execution/cleanup window so a
            # near-expiry queued job cannot lose its valid lease mid-solve.
            job.deadline_at = now + timedelta(seconds=request.time_limit_seconds + 30)
            job.heartbeat_at = now
            job.attempts += 1
            job.updated_at = now
            return ClaimedJob(
                id=job.id,
                lease_token=lease_token,
                request=request,
                cancel_requested=job.cancel_requested,
            )

    async def heartbeat(self, job_id: str, lease_token: str, *, lease_seconds: int = 30) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            job = await session.get(OptimizationJob, job_id, with_for_update=True)
            job = self._validate_lease(job, job_id, lease_token)
            job.heartbeat_at = now
            job.leased_until = now + timedelta(seconds=lease_seconds)
            job.updated_at = now
            return job.cancel_requested

    async def complete(
        self,
        job_id: str,
        lease_token: str,
        *,
        status: OptimizationJobStatus,
        result: OptimizationResult,
    ) -> OptimizationJobRead:
        if status not in {
            OptimizationJobStatus.OPTIMAL,
            OptimizationJobStatus.FEASIBLE,
            OptimizationJobStatus.INFEASIBLE,
            OptimizationJobStatus.TIME_LIMIT,
        }:
            raise ValueError(f"invalid completion status: {status}")
        async with self._session_factory() as session, session.begin():
            job = await session.get(OptimizationJob, job_id, with_for_update=True)
            job = self._validate_lease(job, job_id, lease_token)
            if job.cancel_requested:
                job.status = OptimizationJobStatus.CANCELLED
                job.result_snapshot = None
                job.error_code = None
                job.error_message = None
            else:
                job.status = status
                job.result_snapshot = result.model_dump(mode="json", by_alias=True)
            self._clear_lease(job)
            job.updated_at = datetime.now(UTC)
        return self._to_read(job)

    async def fail(
        self,
        job_id: str,
        lease_token: str,
        *,
        error_code: str,
        error_message: str,
    ) -> OptimizationJobRead:
        async with self._session_factory() as session, session.begin():
            job = await session.get(OptimizationJob, job_id, with_for_update=True)
            job = self._validate_lease(job, job_id, lease_token)
            if job.cancel_requested:
                job.status = OptimizationJobStatus.CANCELLED
                job.result_snapshot = None
                job.error_code = None
                job.error_message = None
            else:
                job.status = OptimizationJobStatus.FAILED
                job.error_code = error_code[:80]
                job.error_message = error_message[:2000]
            self._clear_lease(job)
            job.updated_at = datetime.now(UTC)
        return self._to_read(job)

    @staticmethod
    async def _active_count(session: AsyncSession) -> int:
        statement = (
            select(func.count())
            .select_from(OptimizationJob)
            .where(OptimizationJob.status.in_(ACTIVE_STATUSES))
        )
        return int(await session.scalar(statement) or 0)

    @classmethod
    async def _sweep_active(
        cls,
        session: AsyncSession,
        *,
        now: datetime,
        max_attempts: int,
    ) -> None:
        sweepable_jobs = (
            await session.scalars(
                select(OptimizationJob)
                .where(
                    or_(
                        (
                            (OptimizationJob.status == OptimizationJobStatus.QUEUED)
                            & or_(
                                OptimizationJob.deadline_at <= now,
                                OptimizationJob.attempts >= max_attempts,
                            )
                        ),
                        (
                            (OptimizationJob.status == OptimizationJobStatus.RUNNING)
                            & or_(
                                OptimizationJob.leased_until.is_(None),
                                OptimizationJob.leased_until <= now,
                            )
                        ),
                    )
                )
                .with_for_update()
            )
        ).all()
        for job in sweepable_jobs:
            status = OptimizationJobStatus(job.status)
            lease_expired = status is OptimizationJobStatus.RUNNING and (
                job.leased_until is None or _utc(job.leased_until) <= now
            )
            if lease_expired and job.cancel_requested:
                job.status = OptimizationJobStatus.CANCELLED
                job.result_snapshot = None
                job.error_code = None
                job.error_message = None
            elif _utc(job.deadline_at) <= now:
                job.status = OptimizationJobStatus.TIME_LIMIT
                job.result_snapshot = None
                job.error_code = None
                job.error_message = None
            elif (lease_expired or status is OptimizationJobStatus.QUEUED) and (
                job.attempts >= max_attempts
            ):
                job.status = OptimizationJobStatus.FAILED
                job.result_snapshot = None
                job.error_code = "MAX_ATTEMPTS"
                job.error_message = "optimizer worker retry limit reached"
            else:
                continue
            cls._clear_lease(job)
            job.updated_at = now

    @staticmethod
    async def _prune_terminal(session: AsyncSession, *, older_than: datetime) -> int:
        expired_ids = (
            await session.scalars(
                select(OptimizationJob.id).where(
                    OptimizationJob.status.in_(TERMINAL_STATUSES),
                    OptimizationJob.updated_at < older_than,
                )
            )
        ).all()
        if not expired_ids:
            return 0
        await session.execute(
            delete(OptimizationJob).where(
                OptimizationJob.id.in_(expired_ids),
                OptimizationJob.status.in_(TERMINAL_STATUSES),
                OptimizationJob.updated_at < older_than,
            )
        )
        return len(expired_ids)

    @staticmethod
    def _validate_lease(
        job: OptimizationJob | None,
        job_id: str,
        lease_token: str,
    ) -> OptimizationJob:
        if job is None:
            raise JobNotFoundError(job_id)
        if job.status != OptimizationJobStatus.RUNNING or job.lease_token != lease_token:
            raise InvalidLeaseError(job_id)
        return job

    @staticmethod
    def _clear_lease(job: OptimizationJob) -> None:
        job.lease_token = None
        job.worker_id = None
        job.leased_until = None
        job.heartbeat_at = None

    @staticmethod
    def _to_read(job: OptimizationJob) -> OptimizationJobRead:
        result = (
            OptimizationResult.model_validate(job.result_snapshot)
            if job.result_snapshot is not None
            else None
        )
        return OptimizationJobRead(
            id=job.id,
            status=OptimizationJobStatus(job.status),
            request=OptimizationCreate.model_validate(job.input_snapshot),
            result=result,
            error_code=job.error_code,
            error_message=job.error_message,
            cancel_requested=job.cancel_requested,
            attempts=job.attempts,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )
