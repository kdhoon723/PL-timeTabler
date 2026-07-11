from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, Response, status

from timetabler.api.dependencies import (
    CatalogDependency,
    JobStoreDependency,
    OptimizationRateLimiterDependency,
    SettingsDependency,
)
from timetabler.api.rate_limit import (
    RateLimitExceededError,
    client_key_from_headers,
)
from timetabler.api.schemas import OptimizationCreate, OptimizationJobRead
from timetabler.jobs.store import ActiveJobLimitError, JobNotFoundError

router = APIRouter(prefix="/optimizations", tags=["optimizations"])


@router.post("", response_model=OptimizationJobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_optimization(
    body: OptimizationCreate,
    http_request: Request,
    catalog: CatalogDependency,
    store: JobStoreDependency,
    limiter: OptimizationRateLimiterDependency,
    settings: SettingsDependency,
    response: Response,
) -> OptimizationJobRead:
    snapshot = catalog.snapshot
    if body.semester != snapshot.semester:
        raise HTTPException(status_code=422, detail="unsupported semester")
    if body.dataset_version != snapshot.dataset_version:
        raise HTTPException(status_code=409, detail="catalog version changed; refresh required")
    section_ids = catalog.by_id(body.semester)
    unknown_locked = sorted(set(body.locked_section_ids) - section_ids.keys())
    unknown_selected = sorted(set(body.selected_section_ids) - section_ids.keys())
    if unknown_locked or unknown_selected:
        raise HTTPException(
            status_code=422,
            detail={
                "unknownLockedSectionIds": unknown_locked,
                "unknownSelectedSectionIds": unknown_selected,
            },
        )
    locked_excluded = sorted(
        section_id
        for section_id in set(body.locked_section_ids)
        if section_ids[section_id].course_code in set(body.excluded_course_codes)
    )
    if locked_excluded:
        raise HTTPException(
            status_code=422,
            detail={"lockedSectionsWithExcludedCourses": locked_excluded},
        )
    unavailable_professors = [
        constraint.model_dump(by_alias=True)
        for constraint in body.professor_constraints
        if not any(
            section.course_code == constraint.course_code
            and section.professor == constraint.professor
            for section in section_ids.values()
        )
    ]
    if unavailable_professors:
        raise HTTPException(
            status_code=422,
            detail={"unavailableProfessorConstraints": unavailable_professors},
        )
    client_key = client_key_from_headers(
        http_request.headers.get("CF-Connecting-IP"),
        http_request.client.host if http_request.client is not None else None,
    )
    try:
        await limiter.consume(client_key)
    except RateLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many optimization requests; retry later",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    try:
        job = await store.create(
            body,
            active_limit=settings.optimization_active_job_limit,
            retention=timedelta(hours=settings.optimization_job_retention_hours),
        )
    except ActiveJobLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="optimizer queue is at capacity; retry later",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    response.headers["Location"] = f"/api/v1/optimizations/{job.id}"
    return job


@router.get("/{job_id}", response_model=OptimizationJobRead)
async def get_optimization(job_id: str, store: JobStoreDependency) -> OptimizationJobRead:
    try:
        return await store.get(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="optimization job not found") from exc


@router.delete("/{job_id}", response_model=OptimizationJobRead)
async def cancel_optimization(job_id: str, store: JobStoreDependency) -> OptimizationJobRead:
    try:
        return await store.cancel(job_id)
    except JobNotFoundError as exc:
        raise HTTPException(status_code=404, detail="optimization job not found") from exc
