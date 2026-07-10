from fastapi import APIRouter, HTTPException, Response, status

from timetabler.api.dependencies import CatalogDependency, JobStoreDependency
from timetabler.api.schemas import OptimizationCreate, OptimizationJobRead
from timetabler.jobs.store import JobNotFoundError

router = APIRouter(prefix="/optimizations", tags=["optimizations"])
alias_router = APIRouter(prefix="/optimization-jobs", tags=["optimizations"], include_in_schema=False)


@router.post("", response_model=OptimizationJobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_optimization(
    request: OptimizationCreate,
    catalog: CatalogDependency,
    store: JobStoreDependency,
    response: Response,
) -> OptimizationJobRead:
    snapshot = catalog.snapshot
    if request.semester != snapshot.semester:
        raise HTTPException(status_code=422, detail="unsupported semester")
    if request.dataset_version != snapshot.dataset_version:
        raise HTTPException(status_code=409, detail="catalog version changed; refresh required")
    section_ids = catalog.by_id(request.semester)
    unknown_locked = sorted(set(request.locked_section_ids) - section_ids.keys())
    unknown_selected = sorted(set(request.selected_section_ids) - section_ids.keys())
    if unknown_locked or unknown_selected:
        raise HTTPException(
            status_code=422,
            detail={
                "unknownLockedSectionIds": unknown_locked,
                "unknownSelectedSectionIds": unknown_selected,
            },
        )
    job = await store.create(request)
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

# Stable compatibility surface used by the mobile/web draft client.
alias_router.add_api_route("", create_optimization, methods=["POST"], status_code=status.HTTP_202_ACCEPTED)
alias_router.add_api_route("/{job_id}", get_optimization, methods=["GET"])
alias_router.add_api_route("/{job_id}", cancel_optimization, methods=["DELETE"])
