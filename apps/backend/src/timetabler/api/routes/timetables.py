from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import UTC, datetime
from itertools import combinations, pairwise
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import delete, select

from timetabler.api.dependencies import CatalogDependency, CurrentUserDependency, DatabaseDependency
from timetabler.api.resource_schemas import (
    DeleteResponse,
    SharedTimetableRead,
    TimetableCopyRequest,
    TimetableCreate,
    TimetableDetail,
    TimetableFavoriteUpdate,
    TimetableItem,
    TimetableItemsUpdate,
    TimetableList,
    TimetableMetrics,
    TimetablePreferences,
    TimetableRead,
    TimetableShareCreate,
    TimetableShareRead,
    TimetableUpdate,
)
from timetabler.catalog.models import Section
from timetabler.db.models import SavedTimetable, TimetableShare, User

router = APIRouter(prefix="/timetables", tags=["timetables"])
shared_router = APIRouter(prefix="/shared-timetables", tags=["shared-timetables"])


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _read(model: SavedTimetable) -> TimetableRead:
    return TimetableRead(
        id=model.id,
        name=model.name,
        semester=model.semester,
        data_version=model.dataset_version,
        items=tuple(TimetableItem.model_validate(item) for item in model.items_snapshot),
        preferences=TimetablePreferences.model_validate(model.preferences_snapshot),
        favorite=model.favorite,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _active_sections(
    timetable: SavedTimetable,
    by_id: dict[str, Section],
) -> tuple[Section, ...]:
    return tuple(
        by_id[item["sectionId"]]
        for item in timetable.items_snapshot
        if item.get("role") in {"must", "want"} and item.get("sectionId") in by_id
    )


def _conflicts(sections: tuple[Section, ...]) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for left, right in combinations(sections, 2):
        if any(
            a.day == b.day and a.start_minute < b.end_minute and b.start_minute < a.end_minute
            for a in left.sessions
            for b in right.sessions
        ):
            result.append((left.id, right.id))
    return tuple(result)


def _metrics(sections: tuple[Section, ...]) -> TimetableMetrics:
    days: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for section in sections:
        for meeting in section.sessions:
            days[meeting.day].append((meeting.start_minute, meeting.end_minute))
    gaps = sum(
        max(0, right[0] - left[1])
        for meetings in days.values()
        for left, right in pairwise(sorted(meetings))
    )
    return TimetableMetrics(
        credits=sum(section.credits for section in sections),
        campus_days=len(days),
        gap_minutes=gaps,
    )


def _validate_items(
    body_items: tuple[TimetableItem, ...],
    semester: str,
    data_version: str | None,
    catalog: CatalogDependency,
) -> dict[str, Section]:
    snapshot = catalog.snapshot
    if semester != snapshot.semester:
        raise HTTPException(status_code=422, detail="unsupported semester")
    if data_version is not None and data_version != snapshot.dataset_version:
        raise HTTPException(status_code=409, detail="catalog version changed; refresh required")
    by_id = catalog.by_id(semester)
    item_ids = [item.section_id for item in body_items]
    if len(set(item_ids)) != len(item_ids):
        raise HTTPException(status_code=422, detail="duplicate timetable sections")
    unknown = sorted(set(item_ids) - by_id.keys())
    if unknown:
        raise HTTPException(status_code=422, detail={"unknownSectionIds": unknown})
    active = tuple(by_id[item.section_id] for item in body_items if item.role in {"must", "want"})
    if len({section.course_code for section in active}) != len(active):
        raise HTTPException(status_code=409, detail="multiple sections of the same course")
    conflicts = _conflicts(active)
    if conflicts:
        raise HTTPException(status_code=409, detail={"conflicts": conflicts})
    return by_id


async def _owned(
    database: DatabaseDependency,
    timetable_id: str,
    user: User,
    *,
    for_update: bool = False,
) -> SavedTimetable:
    async with database.session_factory() as session:
        statement = select(SavedTimetable).where(SavedTimetable.id == timetable_id)
        if for_update:
            statement = statement.with_for_update()
        timetable = (await session.scalars(statement)).one_or_none()
    if timetable is None:
        raise HTTPException(status_code=404, detail="timetable not found")
    if timetable.user_id != user.id:
        raise HTTPException(status_code=403, detail="timetable access denied")
    return timetable


async def _detail(
    timetable: SavedTimetable,
    catalog: CatalogDependency,
) -> TimetableDetail:
    try:
        by_id = catalog.by_id(timetable.semester)
    except KeyError:
        by_id = {}
    sections = _active_sections(timetable, by_id)
    return TimetableDetail(
        timetable=_read(timetable),
        sections=sections,
        metrics=_metrics(sections),
        conflict_section_ids=_conflicts(sections),
    )


@router.post("", response_model=TimetableDetail, status_code=status.HTTP_201_CREATED)
async def create_timetable(
    body: TimetableCreate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> TimetableDetail:
    _validate_items(body.items, body.semester, body.data_version, catalog)
    now = datetime.now(UTC)
    timetable = SavedTimetable(
        id=str(uuid4()),
        user_id=user.id,
        name=body.name.strip(),
        semester=body.semester,
        dataset_version=body.data_version or catalog.snapshot.dataset_version,
        items_snapshot=[item.model_dump(mode="json", by_alias=True) for item in body.items],
        preferences_snapshot=body.preferences.model_dump(mode="json", by_alias=True),
        favorite=False,
        created_at=now,
        updated_at=now,
    )
    async with database.session_factory() as session, session.begin():
        session.add(timetable)
    return await _detail(timetable, catalog)


@router.get("", response_model=TimetableList)
async def list_timetables(
    user: CurrentUserDependency,
    database: DatabaseDependency,
    semester: str | None = None,
    favorite: bool | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> TimetableList:
    statement = select(SavedTimetable).where(SavedTimetable.user_id == user.id)
    if semester:
        statement = statement.where(SavedTimetable.semester == semester)
    if favorite is not None:
        statement = statement.where(SavedTimetable.favorite == favorite)
    statement = statement.order_by(SavedTimetable.updated_at.desc())
    async with database.session_factory() as session:
        timetables = (await session.scalars(statement)).all()
    start = (page - 1) * size
    return TimetableList(
        timetables=tuple(_read(item) for item in timetables[start : start + size]),
        total=len(timetables),
    )


@router.get("/history", response_model=TimetableList)
async def timetable_history(
    user: CurrentUserDependency,
    database: DatabaseDependency,
    semester: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
) -> TimetableList:
    return await list_timetables(
        user,
        database,
        semester=semester,
        page=page,
        size=size,
    )


@router.get("/{timetable_id}", response_model=TimetableDetail)
async def get_timetable(
    timetable_id: str,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> TimetableDetail:
    return await _detail(await _owned(database, timetable_id, user), catalog)


@router.patch("/{timetable_id}", response_model=TimetableRead)
async def update_timetable(
    timetable_id: str,
    body: TimetableUpdate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> TimetableRead:
    async with database.session_factory() as session, session.begin():
        timetable = await session.get(SavedTimetable, timetable_id, with_for_update=True)
        if timetable is None:
            raise HTTPException(status_code=404, detail="timetable not found")
        if timetable.user_id != user.id:
            raise HTTPException(status_code=403, detail="timetable access denied")
        values = body.model_dump(exclude_unset=True)
        if "name" in values:
            timetable.name = values["name"].strip()
        if "data_version" in values:
            timetable.dataset_version = values["data_version"]
        if "preferences" in values and body.preferences is not None:
            timetable.preferences_snapshot = body.preferences.model_dump(mode="json", by_alias=True)
        timetable.updated_at = datetime.now(UTC)
    return _read(timetable)


@router.patch("/{timetable_id}/sections", response_model=TimetableDetail)
async def update_timetable_sections(
    timetable_id: str,
    body: TimetableItemsUpdate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> TimetableDetail:
    timetable = await _owned(database, timetable_id, user)
    _validate_items(body.items, timetable.semester, body.data_version, catalog)
    async with database.session_factory() as session, session.begin():
        stored = await session.get(SavedTimetable, timetable_id, with_for_update=True)
        assert stored is not None
        stored.items_snapshot = [item.model_dump(mode="json", by_alias=True) for item in body.items]
        if body.data_version is not None:
            stored.dataset_version = body.data_version
        stored.updated_at = datetime.now(UTC)
    return await _detail(stored, catalog)


@router.delete("/{timetable_id}", response_model=DeleteResponse)
async def delete_timetable(
    timetable_id: str,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> DeleteResponse:
    await _owned(database, timetable_id, user)
    async with database.session_factory() as session, session.begin():
        await session.execute(
            delete(TimetableShare).where(TimetableShare.timetable_id == timetable_id)
        )
        await session.execute(delete(SavedTimetable).where(SavedTimetable.id == timetable_id))
    return DeleteResponse(message="timetable deleted", deleted_at=datetime.now(UTC))


@router.post("/{timetable_id}/copy", response_model=TimetableDetail, status_code=201)
async def copy_timetable(
    timetable_id: str,
    body: TimetableCopyRequest,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> TimetableDetail:
    source = await _owned(database, timetable_id, user)
    now = datetime.now(UTC)
    copied = SavedTimetable(
        id=str(uuid4()),
        user_id=user.id,
        name=body.name.strip() if body.name else f"{source.name} 복사본",
        semester=source.semester,
        dataset_version=source.dataset_version,
        items_snapshot=[dict(item) for item in source.items_snapshot],
        preferences_snapshot=dict(source.preferences_snapshot),
        favorite=False,
        created_at=now,
        updated_at=now,
    )
    async with database.session_factory() as session, session.begin():
        session.add(copied)
    return await _detail(copied, catalog)


@router.patch("/{timetable_id}/favorite", response_model=TimetableRead)
async def update_favorite(
    timetable_id: str,
    body: TimetableFavoriteUpdate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> TimetableRead:
    async with database.session_factory() as session, session.begin():
        timetable = await session.get(SavedTimetable, timetable_id, with_for_update=True)
        if timetable is None:
            raise HTTPException(status_code=404, detail="timetable not found")
        if timetable.user_id != user.id:
            raise HTTPException(status_code=403, detail="timetable access denied")
        timetable.favorite = body.favorite
        timetable.updated_at = datetime.now(UTC)
    return _read(timetable)


@router.post("/{timetable_id}/shares", response_model=TimetableShareRead, status_code=201)
async def create_share(
    timetable_id: str,
    body: TimetableShareCreate,
    request: Request,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> TimetableShareRead:
    await _owned(database, timetable_id, user)
    if body.expires_at is not None and _utc(body.expires_at) <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="share expiry must be in the future")
    share = TimetableShare(
        share_code=secrets.token_urlsafe(9),
        timetable_id=timetable_id,
        created_by=user.id,
        expires_at=body.expires_at,
        created_at=datetime.now(UTC),
    )
    async with database.session_factory() as session, session.begin():
        session.add(share)
    return TimetableShareRead(
        share_code=share.share_code,
        share_url=str(request.base_url).rstrip("/") + f"/shared/{share.share_code}",
        expires_at=share.expires_at,
    )


async def _shared(
    share_code: str,
    database: DatabaseDependency,
) -> SavedTimetable:
    async with database.session_factory() as session:
        share = await session.get(TimetableShare, share_code)
        if share is None:
            raise HTTPException(status_code=404, detail="shared timetable not found")
        if share.expires_at is not None and _utc(share.expires_at) <= datetime.now(UTC):
            raise HTTPException(status_code=410, detail="shared timetable expired")
        timetable = await session.get(SavedTimetable, share.timetable_id)
    if timetable is None:
        raise HTTPException(status_code=404, detail="shared timetable not found")
    return timetable


@shared_router.get("/{share_code}", response_model=SharedTimetableRead)
async def get_shared_timetable(
    share_code: str,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> SharedTimetableRead:
    timetable = await _shared(share_code, database)
    detail = await _detail(timetable, catalog)
    return SharedTimetableRead(
        timetable=detail.timetable,
        sections=detail.sections,
        metrics=detail.metrics,
    )


@shared_router.post("/{share_code}/copy", response_model=TimetableDetail, status_code=201)
async def copy_shared_timetable(
    share_code: str,
    body: TimetableCopyRequest,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> TimetableDetail:
    source = await _shared(share_code, database)
    now = datetime.now(UTC)
    copied = SavedTimetable(
        id=str(uuid4()),
        user_id=user.id,
        name=body.name.strip() if body.name else f"{source.name} 복사본",
        semester=source.semester,
        dataset_version=source.dataset_version,
        items_snapshot=[dict(item) for item in source.items_snapshot],
        preferences_snapshot=dict(source.preferences_snapshot),
        favorite=False,
        created_at=now,
        updated_at=now,
    )
    async with database.session_factory() as session, session.begin():
        session.add(copied)
    return await _detail(copied, catalog)
