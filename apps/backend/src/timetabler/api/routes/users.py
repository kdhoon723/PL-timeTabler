from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import delete, select

from timetabler.api.dependencies import (
    AuthServiceDependency,
    CurrentUserDependency,
    DatabaseDependency,
    SettingsDependency,
)
from timetabler.api.resource_schemas import (
    ConsentCreate,
    ConsentRead,
    DeleteResponse,
    UserDeleteRequest,
    UserRead,
    UserUpdate,
)
from timetabler.db.models import (
    CompletedCourse,
    CourseReview,
    PrivacyConsent,
    SavedTimetable,
    TimetableShare,
    User,
)

router = APIRouter(prefix="/users/me", tags=["users"])


def _user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        student_number=user.student_number,
        name=user.name,
        grade=user.grade,
        department=user.department,
        admission_year=user.admission_year,
        entry_type=user.entry_type,
        student_type=user.student_type,
        section_group=user.section_group,
        major_path=user.major_path,
        profile_completed=user.profile_completed,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _department_names(data_root: Path) -> set[str]:
    path = data_root / "requirements" / "normalized" / "department-sources-2026.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {str(item["academicUnit"]) for item in payload.get("departments", [])}
    except (OSError, ValueError, TypeError, KeyError):
        return set()


@router.get("", response_model=UserRead)
async def get_me(user: CurrentUserDependency) -> UserRead:
    return _user_read(user)


@router.patch("", response_model=UserRead)
async def update_me(
    body: UserUpdate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    settings: SettingsDependency,
) -> UserRead:
    values = body.model_dump(exclude_unset=True)
    department = values.get("department")
    if department is not None and department not in _department_names(settings.data_root):
        raise HTTPException(status_code=404, detail="department not found")
    async with database.session_factory() as session, session.begin():
        stored = await session.get(User, user.id, with_for_update=True)
        if stored is None:
            raise HTTPException(status_code=404, detail="account not found")
        for key, value in values.items():
            setattr(stored, key, value.strip() if isinstance(value, str) else value)
        has_consent = bool(
            await session.scalar(
                select(PrivacyConsent.id)
                .where(
                    PrivacyConsent.user_id == stored.id,
                    PrivacyConsent.agreed.is_(True),
                )
                .limit(1)
            )
        )
        stored.profile_completed = bool(
            stored.name and stored.grade and stored.department and has_consent
        )
        stored.updated_at = datetime.now(UTC)
    return _user_read(stored)


@router.post("/consents", response_model=ConsentRead, status_code=status.HTTP_201_CREATED)
async def create_consent(
    body: ConsentCreate,
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> ConsentRead:
    if not body.agreed:
        raise HTTPException(status_code=400, detail="privacy consent must be agreed")
    now = datetime.now(UTC)
    consent = PrivacyConsent(
        id=str(uuid4()),
        user_id=user.id,
        consent_version=body.consent_version,
        agreed=True,
        agreed_at=now,
    )
    async with database.session_factory() as session, session.begin():
        session.add(consent)
        stored = await session.get(User, user.id, with_for_update=True)
        if stored is not None and stored.name and stored.grade and stored.department:
            stored.profile_completed = True
            stored.updated_at = now
    return ConsentRead(
        id=consent.id,
        consent_version=consent.consent_version,
        agreed=consent.agreed,
        agreed_at=consent.agreed_at,
    )


@router.get("/consents", response_model=tuple[ConsentRead, ...])
async def list_consents(
    user: CurrentUserDependency,
    database: DatabaseDependency,
) -> tuple[ConsentRead, ...]:
    async with database.session_factory() as session:
        consents = (
            await session.scalars(
                select(PrivacyConsent)
                .where(PrivacyConsent.user_id == user.id)
                .order_by(PrivacyConsent.agreed_at.desc())
            )
        ).all()
    return tuple(
        ConsentRead(
            id=item.id,
            consent_version=item.consent_version,
            agreed=item.agreed,
            agreed_at=item.agreed_at,
        )
        for item in consents
    )


@router.delete("", response_model=DeleteResponse)
async def delete_me(
    body: UserDeleteRequest,
    response: Response,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    auth: AuthServiceDependency,
    settings: SettingsDependency,
) -> DeleteResponse:
    if body.confirmation not in {"회원탈퇴", user.student_number}:
        raise HTTPException(status_code=400, detail="account deletion confirmation required")
    deleted_at = datetime.now(UTC)
    async with database.session_factory() as session, session.begin():
        timetable_ids = tuple(
            await session.scalars(
                select(SavedTimetable.id).where(SavedTimetable.user_id == user.id)
            )
        )
        if timetable_ids:
            await session.execute(
                delete(TimetableShare).where(TimetableShare.timetable_id.in_(timetable_ids))
            )
        await session.execute(delete(TimetableShare).where(TimetableShare.created_by == user.id))
        await session.execute(delete(CourseReview).where(CourseReview.user_id == user.id))
        await session.execute(delete(CompletedCourse).where(CompletedCourse.user_id == user.id))
        await session.execute(delete(PrivacyConsent).where(PrivacyConsent.user_id == user.id))
        await session.execute(delete(SavedTimetable).where(SavedTimetable.user_id == user.id))
        await session.execute(delete(User).where(User.id == user.id))
    await auth.delete_account_records(user.student_number)
    response.delete_cookie(
        key=settings.auth_session_cookie_name,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return DeleteResponse(message="account deleted", deleted_at=deleted_at)
