from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Select, or_, select
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


class OptimizationJobStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, request: OptimizationCreate) -> OptimizationJobRead:
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
        async with self._session_factory() as session:
            session.add(job)
            await session.commit()
            await session.refresh(job)
        return self._to_read(job)

    async def get(self, job_id: str) -> OptimizationJobRead:
        async with self._session_factory() as session:
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
                or_(
                    OptimizationJob.status == OptimizationJobStatus.QUEUED,
                    (
                        (OptimizationJob.status == OptimizationJobStatus.RUNNING)
                        & (OptimizationJob.leased_until < now)
                    ),
                ),
            )
            .order_by(OptimizationJob.created_at, OptimizationJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        async with self._session_factory() as session, session.begin():
            job = (await session.execute(claimable)).scalar_one_or_none()
            if job is None:
                return None
            lease_token = str(uuid4())
            job.status = OptimizationJobStatus.RUNNING
            job.lease_token = lease_token
            job.worker_id = worker_id
            job.leased_until = now + timedelta(seconds=lease_seconds)
            job.heartbeat_at = now
            job.attempts += 1
            job.updated_at = now
            return ClaimedJob(
                id=job.id,
                lease_token=lease_token,
                request=OptimizationCreate.model_validate(job.input_snapshot),
                cancel_requested=job.cancel_requested,
            )

    async def heartbeat(self, job_id: str, lease_token: str, *, lease_seconds: int = 30) -> bool:
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            job = await session.get(OptimizationJob, job_id, with_for_update=True)
            self._validate_lease(job, job_id, lease_token)
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
            self._validate_lease(job, job_id, lease_token)
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
            self._validate_lease(job, job_id, lease_token)
            job.status = OptimizationJobStatus.FAILED
            job.error_code = error_code[:80]
            job.error_message = error_message[:2000]
            self._clear_lease(job)
            job.updated_at = datetime.now(UTC)
        return self._to_read(job)

    @staticmethod
    def _validate_lease(
        job: OptimizationJob | None,
        job_id: str,
        lease_token: str,
    ) -> None:
        if job is None:
            raise JobNotFoundError(job_id)
        if job.status != OptimizationJobStatus.RUNNING or job.lease_token != lease_token:
            raise InvalidLeaseError(job_id)

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
