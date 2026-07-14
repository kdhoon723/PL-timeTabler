from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from timetabler.api.dependencies import (
    CatalogDependency,
    CurrentUserDependency,
    DatabaseDependency,
    OptionalUserDependency,
)
from timetabler.api.resource_schemas import (
    RatingSummary,
    ReviewCreate,
    ReviewDeleteResponse,
    ReviewList,
    ReviewMutationResponse,
    ReviewRead,
    ReviewUpdate,
)
from timetabler.db.models import CourseReview, User

course_router = APIRouter(prefix="/courses", tags=["reviews"])
review_router = APIRouter(prefix="/reviews", tags=["reviews"])
my_router = APIRouter(prefix="/users/me/reviews", tags=["reviews"])


def popularity_score(average_rating: float, review_count: int) -> float:
    if review_count <= 0:
        return 0.0
    return round(average_rating * math.log2(review_count + 1), 3)


async def rating_summary(
    session: AsyncSession,
    course_code: str,
    professor: str | None = None,
) -> RatingSummary:
    statement = select(func.avg(CourseReview.rating), func.count(CourseReview.id)).where(
        CourseReview.course_code == course_code
    )
    if professor is not None:
        statement = statement.where(CourseReview.professor == professor)
    average, count = (await session.execute(statement)).one()
    review_count = int(count or 0)
    average_rating = round(float(average or 0), 2)
    return RatingSummary(
        average_rating=average_rating,
        review_count=review_count,
        popularity_score=popularity_score(average_rating, review_count),
    )


def _read(review: CourseReview, *, mine: bool) -> ReviewRead:
    return ReviewRead(
        id=review.id,
        course_code=review.course_code,
        course_name=review.course_name,
        professor=review.professor,
        semester=review.semester,
        rating=review.rating,
        content=review.content,
        mine=mine,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def _course_name(catalog: CatalogDependency, course_code: str) -> str:
    section = next(
        (item for item in catalog.snapshot.sections if item.course_code == course_code), None
    )
    if section is None:
        raise HTTPException(status_code=404, detail="course not found")
    return section.name


@course_router.get("/{course_code}/reviews", response_model=ReviewList)
async def list_course_reviews(
    course_code: str,
    database: DatabaseDependency,
    catalog: CatalogDependency,
    user: OptionalUserDependency,
    professor: str | None = None,
    semester: str | None = None,
    sort: str = Query(default="NEWEST", pattern="^(NEWEST|RATING)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> ReviewList:
    _course_name(catalog, course_code)
    statement = select(CourseReview).where(CourseReview.course_code == course_code)
    if professor is not None:
        statement = statement.where(CourseReview.professor == professor)
    if semester is not None:
        statement = statement.where(CourseReview.semester == semester)
    order = (
        (CourseReview.rating.desc(), CourseReview.created_at.desc())
        if sort == "RATING"
        else (CourseReview.created_at.desc(),)
    )
    statement = statement.order_by(*order)
    async with database.session_factory() as session:
        all_reviews = (await session.scalars(statement)).all()
        summary = await rating_summary(session, course_code, professor)
    start = (page - 1) * size
    return ReviewList(
        reviews=tuple(
            _read(item, mine=user is not None and item.user_id == user.id)
            for item in all_reviews[start : start + size]
        ),
        rating_summary=summary,
        total=len(all_reviews),
    )


@course_router.post(
    "/{course_code}/reviews",
    response_model=ReviewMutationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    course_code: str,
    body: ReviewCreate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    catalog: CatalogDependency,
) -> ReviewMutationResponse:
    course_name = _course_name(catalog, course_code)
    if body.professor is not None and not any(
        section.course_code == course_code and section.professor == body.professor
        for section in catalog.snapshot.sections
    ):
        raise HTTPException(status_code=404, detail="professor offering not found")
    now = datetime.now(UTC)
    review = CourseReview(
        id=str(uuid4()),
        user_id=user.id,
        course_code=course_code,
        course_name=course_name,
        professor=body.professor,
        semester=body.semester,
        rating=body.rating,
        content=body.content.strip(),
        created_at=now,
        updated_at=now,
    )
    try:
        async with database.session_factory() as session, session.begin():
            duplicate = (
                await session.scalars(
                    select(CourseReview).where(
                        CourseReview.user_id == user.id,
                        CourseReview.course_code == course_code,
                        CourseReview.professor == body.professor,
                        CourseReview.semester == body.semester,
                    )
                )
            ).one_or_none()
            if duplicate is not None:
                raise HTTPException(status_code=409, detail="review already exists")
            session.add(review)
        async with database.session_factory() as session:
            summary = await rating_summary(session, course_code, body.professor)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="review already exists") from exc
    return ReviewMutationResponse(review=_read(review, mine=True), rating_summary=summary)


@course_router.get("/{course_code}/ratings", response_model=RatingSummary)
async def get_rating_summary(
    course_code: str,
    database: DatabaseDependency,
    catalog: CatalogDependency,
    professor: str | None = None,
) -> RatingSummary:
    _course_name(catalog, course_code)
    async with database.session_factory() as session:
        return await rating_summary(session, course_code, professor)


async def _review_for_owner(
    review_id: str,
    user: User,
    database: DatabaseDependency,
) -> CourseReview:
    async with database.session_factory() as session:
        review = await session.get(CourseReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="review not found")
    if review.user_id != user.id:
        raise HTTPException(status_code=403, detail="review access denied")
    return review


@review_router.patch("/{review_id}", response_model=ReviewMutationResponse)
async def update_review(
    review_id: str,
    body: ReviewUpdate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> ReviewMutationResponse:
    await _review_for_owner(review_id, user, database)
    async with database.session_factory() as session, session.begin():
        review = await session.get(CourseReview, review_id, with_for_update=True)
        assert review is not None
        values = body.model_dump(exclude_unset=True)
        if "rating" in values:
            review.rating = values["rating"]
        if "content" in values:
            review.content = values["content"].strip()
        review.updated_at = datetime.now(UTC)
    async with database.session_factory() as session:
        summary = await rating_summary(session, review.course_code, review.professor)
    return ReviewMutationResponse(review=_read(review, mine=True), rating_summary=summary)


@review_router.delete("/{review_id}", response_model=ReviewDeleteResponse)
async def delete_review(
    review_id: str,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> ReviewDeleteResponse:
    review = await _review_for_owner(review_id, user, database)
    async with database.session_factory() as session, session.begin():
        await session.execute(delete(CourseReview).where(CourseReview.id == review_id))
    async with database.session_factory() as session:
        summary = await rating_summary(session, review.course_code, review.professor)
    return ReviewDeleteResponse(message="review deleted", rating_summary=summary)


@my_router.get("", response_model=ReviewList)
async def list_my_reviews(
    user: CurrentUserDependency,
    database: DatabaseDependency,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=200),
) -> ReviewList:
    async with database.session_factory() as session:
        reviews = (
            await session.scalars(
                select(CourseReview)
                .where(CourseReview.user_id == user.id)
                .order_by(CourseReview.created_at.desc())
            )
        ).all()
    start = (page - 1) * size
    return ReviewList(
        reviews=tuple(_read(item, mine=True) for item in reviews[start : start + size]),
        rating_summary=RatingSummary(
            average_rating=round(sum(item.rating for item in reviews) / len(reviews), 2)
            if reviews
            else 0,
            review_count=len(reviews),
            popularity_score=0,
        ),
        total=len(reviews),
    )
