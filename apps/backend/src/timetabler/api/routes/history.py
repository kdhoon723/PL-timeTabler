from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from timetabler.api.dependencies import CurrentUserDependency, DatabaseDependency
from timetabler.api.resource_schemas import (
    HistoricalCourseImport,
    HistoricalCourseImportResponse,
    HistoricalOfferingDetail,
    HistoricalOfferingList,
    HistoricalOfferingSummary,
    HistoricalSemesterList,
    HistoricalSemesterRead,
)
from timetabler.api.routes.completed_courses import _all_for_user, _read
from timetabler.db.models import CompletedCourse, HistoricalCourseOffering, HistoricalTermDataset
from timetabler.types import normalize_search_text

router = APIRouter(prefix="/history", tags=["history"])
import_router = APIRouter(prefix="/users/me/completed-courses", tags=["completed-courses"])


def _summary(item: HistoricalCourseOffering) -> HistoricalOfferingSummary:
    return HistoricalOfferingSummary(
        id=item.id,
        semester=f"{item.academic_year}-{item.term_code}",
        academic_year=item.academic_year,
        term_code=item.term_code,
        course_code=item.course_code,
        section_code=item.section_code,
        korean_name=item.korean_name,
        english_name=item.english_name,
        professor_name=item.professor_name,
        completion_category=item.completion_category,
        credits=item.credits,
        lecture_hours=item.lecture_hours,
        practice_hours=item.practice_hours,
        raw_lecture_time=item.raw_lecture_time,
        raw_location=item.raw_location,
        target_grade=item.target_grade,
        listing_status=item.listing_status,
        detail_status=item.detail_status,
        category_contexts=item.category_contexts,
        department_contexts=item.department_contexts,
    )


@router.get("/semesters", response_model=HistoricalSemesterList)
async def list_historical_semesters(
    database: DatabaseDependency,
) -> HistoricalSemesterList:
    async with database.session_factory() as session:
        datasets = list((await session.scalars(select(HistoricalTermDataset))).all())
    term_order = {"1": 1, "11": 2, "2": 3, "22": 4}
    datasets.sort(
        key=lambda item: (item.academic_year, term_order.get(item.term_code, 0)), reverse=True
    )
    return HistoricalSemesterList(
        semesters=tuple(
            HistoricalSemesterRead(
                semester=item.id,
                academic_year=item.academic_year,
                term_code=item.term_code,
                term_name=item.term_name,
                data_status=item.data_status,
                course_count=item.record_count,
                collected_at=item.collected_at,
            )
            for item in datasets
        ),
        total_courses=sum(item.record_count for item in datasets),
    )


@router.get("/courses", response_model=HistoricalOfferingList)
async def list_historical_courses(
    database: DatabaseDependency,
    semester: str = Query(pattern=r"^\d{4}-(?:1|2|11|22)$"),
    q: str | None = Query(default=None, max_length=120),
    department: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=160),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=30, ge=1, le=100),
) -> HistoricalOfferingList:
    query = select(HistoricalCourseOffering).where(HistoricalCourseOffering.dataset_id == semester)
    if q:
        for token in q.split():
            if normalized := normalize_search_text(token):
                query = query.where(HistoricalCourseOffering.search_text.contains(normalized))
    if department and (normalized_department := normalize_search_text(department)):
        query = query.where(
            HistoricalCourseOffering.department_search_text.contains(normalized_department)
        )
    if category:
        query = query.where(HistoricalCourseOffering.completion_category == category)
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    query = (
        query.order_by(
            HistoricalCourseOffering.korean_name,
            HistoricalCourseOffering.course_code,
            HistoricalCourseOffering.section_code,
        )
        .offset((page - 1) * size)
        .limit(size)
    )
    async with database.session_factory() as session:
        total = int((await session.scalar(count_query)) or 0)
        courses = list((await session.scalars(query)).all())
    return HistoricalOfferingList(
        courses=tuple(_summary(item) for item in courses),
        page=page,
        size=size,
        total=total,
    )


@router.get("/courses/{offering_id}", response_model=HistoricalOfferingDetail)
async def get_historical_course(
    offering_id: str,
    database: DatabaseDependency,
) -> HistoricalOfferingDetail:
    async with database.session_factory() as session:
        item = await session.get(HistoricalCourseOffering, offering_id)
    if item is None:
        raise HTTPException(status_code=404, detail="historical course offering not found")
    return HistoricalOfferingDetail(**_summary(item).model_dump(), raw_payload=item.raw_payload)


def _category(item: HistoricalCourseOffering) -> tuple[str, str | None]:
    contexts = item.category_contexts
    preferred = next((context for context in contexts if context.get("areaName")), None)
    selected = preferred or (contexts[0] if contexts else {})
    category = str(selected.get("name") or item.completion_category or "일반선택")
    area_value = selected.get("areaName")
    return category, str(area_value) if area_value else None


@import_router.post("/import-history", response_model=HistoricalCourseImportResponse)
async def import_historical_courses(
    body: HistoricalCourseImport,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> HistoricalCourseImportResponse:
    requested_ids = list(dict.fromkeys(body.offering_ids))
    async with database.session_factory() as session:
        offerings = list(
            (
                await session.scalars(
                    select(HistoricalCourseOffering).where(
                        HistoricalCourseOffering.id.in_(requested_ids)
                    )
                )
            ).all()
        )
    by_id = {item.id: item for item in offerings}
    existing = await _all_for_user(database, user.id)
    existing_offering_ids = {
        item.historical_offering_id for item in existing if item.historical_offering_id
    }
    existing_codes = {item.course_code for item in existing if item.course_code}
    now = datetime.now(UTC)
    imported: list[CompletedCourse] = []
    skipped: list[str] = []
    for offering_id in requested_ids:
        offering = by_id.get(offering_id)
        if (
            offering is None
            or offering.id in existing_offering_ids
            or offering.course_code in existing_codes
        ):
            skipped.append(offering_id)
            continue
        category, area = _category(offering)
        item = CompletedCourse(
            id=str(uuid4()),
            user_id=user.id,
            historical_offering_id=offering.id,
            course_code=offering.course_code,
            section_code=offering.section_code,
            course_name=offering.korean_name,
            credits=offering.credits or 0,
            category=category,
            area=area,
            semester=f"{offering.academic_year}-{offering.term_code}",
            status=body.status,
            input_source="HISTORICAL_TIMETABLE",
            source_snapshot=offering.raw_payload,
            created_at=now,
            updated_at=now,
        )
        existing_codes.add(offering.course_code)
        existing_offering_ids.add(offering.id)
        imported.append(item)
    async with database.session_factory() as session, session.begin():
        session.add_all(imported)
    return HistoricalCourseImportResponse(
        imported_courses=tuple(_read(item) for item in imported),
        skipped_offering_ids=tuple(skipped),
    )
