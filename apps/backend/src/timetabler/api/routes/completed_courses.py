from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, select

from timetabler.api.dependencies import CatalogDependency, CurrentUserDependency, DatabaseDependency
from timetabler.api.resource_schemas import (
    CompletedCourseCreate,
    CompletedCourseList,
    CompletedCourseRead,
    CompletedCourseUpdate,
    CreditSummary,
    DeleteResponse,
    TimetableCourseImport,
    TimetableCourseImportResponse,
)
from timetabler.db.models import CompletedCourse, SavedTimetable, User
from timetabler.types import normalize_search_text

router = APIRouter(prefix="/users/me/completed-courses", tags=["completed-courses"])


def _read(item: CompletedCourse) -> CompletedCourseRead:
    return CompletedCourseRead(
        id=item.id,
        course_code=item.course_code,
        course_name=item.course_name,
        credits=item.credits,
        category=item.category,
        area=item.area,
        semester=item.semester,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _area_from_category(category: str) -> str | None:
    if not category.startswith("교양선택("):
        return None
    return category.removeprefix("교양선택(").removesuffix(")")


def _summary(items: list[CompletedCourse] | tuple[CompletedCourse, ...]) -> CreditSummary:
    completed = [item for item in items if item.status == "COMPLETED"]
    area_credits: dict[str, float] = defaultdict(float)
    for item in completed:
        area = item.area or _area_from_category(item.category)
        if area:
            area_credits[area] += item.credits
    return CreditSummary(
        total_credits=round(sum(item.credits for item in completed), 2),
        major_credits=round(
            sum(item.credits for item in completed if item.category.startswith("전공")), 2
        ),
        liberal_credits=round(
            sum(item.credits for item in completed if item.category.startswith("교양")), 2
        ),
        area_credits={key: round(value, 2) for key, value in sorted(area_credits.items())},
    )


async def _all_for_user(database: DatabaseDependency, user_id: str) -> list[CompletedCourse]:
    async with database.session_factory() as session:
        return list(
            (
                await session.scalars(
                    select(CompletedCourse)
                    .where(CompletedCourse.user_id == user_id)
                    .order_by(CompletedCourse.updated_at.desc())
                )
            ).all()
        )


def _duplicate(items: list[CompletedCourse], body: CompletedCourseCreate) -> bool:
    normalized = normalize_search_text(body.course_name)
    return any(
        (body.course_code and item.course_code == body.course_code)
        or (
            normalize_search_text(item.course_name) == normalized and item.semester == body.semester
        )
        for item in items
    )


@router.get("", response_model=CompletedCourseList)
async def list_completed_courses(
    user: CurrentUserDependency,
    database: DatabaseDependency,
    status_filter: str | None = Query(
        default=None, alias="status", pattern="^(IN_PROGRESS|COMPLETED)$"
    ),
    semester: str | None = None,
    category: str | None = None,
) -> CompletedCourseList:
    all_items = await _all_for_user(database, user.id)
    filtered = [
        item
        for item in all_items
        if (status_filter is None or item.status == status_filter)
        and (semester is None or item.semester == semester)
        and (category is None or item.category == category)
    ]
    return CompletedCourseList(
        completed_courses=tuple(_read(item) for item in filtered),
        credit_summary=_summary(all_items),
    )


@router.get("/summary", response_model=CreditSummary)
async def get_credit_summary(
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> CreditSummary:
    return _summary(await _all_for_user(database, user.id))


@router.post("", response_model=CompletedCourseRead, status_code=status.HTTP_201_CREATED)
async def create_completed_course(
    body: CompletedCourseCreate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> CompletedCourseRead:
    existing = await _all_for_user(database, user.id)
    if _duplicate(existing, body):
        raise HTTPException(status_code=409, detail="course already registered")
    now = datetime.now(UTC)
    item = CompletedCourse(
        id=str(uuid4()),
        user_id=user.id,
        course_code=body.course_code,
        course_name=body.course_name.strip(),
        credits=body.credits,
        category=body.category.strip(),
        area=body.area.strip() if body.area else _area_from_category(body.category),
        semester=body.semester,
        status=body.status,
        created_at=now,
        updated_at=now,
    )
    async with database.session_factory() as session, session.begin():
        session.add(item)
    return _read(item)


@router.post("/import-timetable", response_model=TimetableCourseImportResponse)
async def import_timetable_courses(
    body: TimetableCourseImport,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> TimetableCourseImportResponse:
    async with database.session_factory() as session:
        timetable = await session.get(SavedTimetable, body.timetable_id)
    if timetable is None:
        raise HTTPException(status_code=404, detail="timetable not found")
    if timetable.user_id != user.id:
        raise HTTPException(status_code=403, detail="timetable access denied")
    try:
        by_id = catalog.by_id(timetable.semester)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="semester catalog not found") from exc
    existing = await _all_for_user(database, user.id)
    existing_codes = {item.course_code for item in existing if item.course_code}
    imported: list[CompletedCourse] = []
    skipped: list[str] = []
    now = datetime.now(UTC)
    for snapshot in timetable.items_snapshot:
        if snapshot.get("role") not in {"must", "want"}:
            continue
        section = by_id.get(str(snapshot.get("sectionId")))
        if section is None:
            continue
        if section.course_code in existing_codes:
            skipped.append(section.course_code)
            continue
        item = CompletedCourse(
            id=str(uuid4()),
            user_id=user.id,
            course_code=section.course_code,
            course_name=section.name,
            credits=section.credits,
            category=section.category,
            area=_area_from_category(section.category),
            semester=timetable.semester,
            status=body.status,
            created_at=now,
            updated_at=now,
        )
        existing_codes.add(section.course_code)
        imported.append(item)
    async with database.session_factory() as session, session.begin():
        session.add_all(imported)
    return TimetableCourseImportResponse(
        imported_courses=tuple(_read(item) for item in imported),
        skipped_courses=tuple(skipped),
    )


async def _owned(
    completed_course_id: str,
    user: User,
    database: DatabaseDependency,
) -> CompletedCourse:
    async with database.session_factory() as session:
        item = await session.get(CompletedCourse, completed_course_id)
    if item is None:
        raise HTTPException(status_code=404, detail="completed course not found")
    if item.user_id != user.id:
        raise HTTPException(status_code=403, detail="completed course access denied")
    return item


@router.patch("/{completed_course_id}", response_model=CompletedCourseRead)
async def update_completed_course(
    completed_course_id: str,
    body: CompletedCourseUpdate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> CompletedCourseRead:
    await _owned(completed_course_id, user, database)
    async with database.session_factory() as session, session.begin():
        item = await session.get(CompletedCourse, completed_course_id, with_for_update=True)
        assert item is not None
        values = body.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(item, key, value.strip() if isinstance(value, str) else value)
        if "category" in values and "area" not in values:
            item.area = _area_from_category(item.category)
        item.updated_at = datetime.now(UTC)
    return _read(item)


@router.delete("/{completed_course_id}", response_model=DeleteResponse)
async def delete_completed_course(
    completed_course_id: str,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> DeleteResponse:
    await _owned(completed_course_id, user, database)
    async with database.session_factory() as session, session.begin():
        await session.execute(
            delete(CompletedCourse).where(CompletedCourse.id == completed_course_id)
        )
    return DeleteResponse(message="completed course deleted", deleted_at=datetime.now(UTC))
