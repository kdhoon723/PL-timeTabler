from collections import defaultdict
from datetime import timedelta
from itertools import combinations, pairwise

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
from timetabler.api.schemas import (
    CandidateCompareRequest,
    CandidateCompareResponse,
    CandidateComparisonRead,
    CandidateMetrics,
    CandidateSwapRead,
    OptimizationCreate,
    OptimizationJobRead,
)
from timetabler.catalog.models import Section
from timetabler.jobs.store import ActiveJobLimitError, JobNotFoundError

router = APIRouter(prefix="/optimizations", tags=["optimizations"])


def _candidate_conflicts(sections: tuple[Section, ...]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (left.id, right.id)
        for left, right in combinations(sections, 2)
        if any(
            first.day == second.day
            and first.start_minute < second.end_minute
            and second.start_minute < first.end_minute
            for first in left.sessions
            for second in right.sessions
        )
    )


def _candidate_metrics(sections: tuple[Section, ...]) -> CandidateMetrics:
    meetings_by_day: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for section in sections:
        for meeting in section.sessions:
            meetings_by_day[meeting.day].append((meeting.start_minute, meeting.end_minute))
    meetings = [meeting for day in meetings_by_day.values() for meeting in day]
    gap_minutes = sum(
        max(0, right[0] - left[1])
        for day in meetings_by_day.values()
        for left, right in pairwise(sorted(day))
    )
    return CandidateMetrics(
        total_credits=sum(section.credits for section in sections),
        campus_days=len(meetings_by_day),
        gap_minutes=gap_minutes,
        first_class_minute=min((meeting[0] for meeting in meetings), default=None),
        last_class_minute=max((meeting[1] for meeting in meetings), default=None),
        unknown_time_sections=sum(not section.sessions for section in sections),
    )


@router.post("/compare", response_model=CandidateCompareResponse)
async def compare_candidates(
    body: CandidateCompareRequest,
    catalog: CatalogDependency,
) -> CandidateCompareResponse:
    by_id = catalog.by_id(catalog.snapshot.semester)
    all_ids = set(body.current_section_ids)
    for candidate in body.candidate_section_ids:
        all_ids.update(candidate)
    unknown = sorted(all_ids - by_id.keys())
    if unknown:
        raise HTTPException(status_code=404, detail={"unknownSectionIds": unknown})

    current = tuple(by_id[section_id] for section_id in body.current_section_ids)
    current_ids = set(body.current_section_ids)
    current_by_course = {section.course_code: section for section in current}
    comparisons: list[CandidateComparisonRead] = []
    for rank, candidate_ids in enumerate(body.candidate_section_ids, start=1):
        sections = tuple(by_id[section_id] for section_id in candidate_ids)
        if len({section.course_code for section in sections}) != len(sections):
            raise HTTPException(
                status_code=400,
                detail={"candidateRank": rank, "reason": "multiple sections of same course"},
            )
        selected_ids = set(candidate_ids)
        selected_by_course = {section.course_code: section for section in sections}
        swapped = tuple(
            CandidateSwapRead(from_section_id=before.id, to_section_id=after.id)
            for course_code, before in current_by_course.items()
            if (after := selected_by_course.get(course_code)) is not None
            and after.id != before.id
        )
        swapped_from = {item.from_section_id for item in swapped}
        swapped_to = {item.to_section_id for item in swapped}
        comparisons.append(
            CandidateComparisonRead(
                rank=rank,
                section_ids=candidate_ids,
                metrics=_candidate_metrics(sections),
                added=tuple(sorted(selected_ids - current_ids - swapped_to)),
                removed=tuple(sorted(current_ids - selected_ids - swapped_from)),
                swapped=swapped,
                conflicts=_candidate_conflicts(sections),
            )
        )
    return CandidateCompareResponse(candidates=tuple(comparisons))


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
