from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import select

from timetabler.api.rate_limit import SlidingWindowRateLimiter
from timetabler.auth.service import AuthService
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import Settings
from timetabler.db.models import User
from timetabler.db.session import Database
from timetabler.jobs.store import OptimizationJobStore


def get_catalog(request: Request) -> CatalogRepository:
    return cast(CatalogRepository, request.app.state.catalog)


def get_database(request: Request) -> Database:
    return cast(Database, request.app.state.database)


def get_job_store(request: Request) -> OptimizationJobStore:
    return cast(OptimizationJobStore, request.app.state.job_store)


def get_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_optimization_rate_limiter(request: Request) -> SlidingWindowRateLimiter:
    return cast(SlidingWindowRateLimiter, request.app.state.optimization_rate_limiter)


def get_auth_service(request: Request) -> AuthService:
    return cast(AuthService, request.app.state.auth_service)


CatalogDependency = Annotated[CatalogRepository, Depends(get_catalog)]
DatabaseDependency = Annotated[Database, Depends(get_database)]
JobStoreDependency = Annotated[OptimizationJobStore, Depends(get_job_store)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
OptimizationRateLimiterDependency = Annotated[
    SlidingWindowRateLimiter, Depends(get_optimization_rate_limiter)
]
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


async def require_current_user(
    request: Request,
    response: Response,
    auth: AuthServiceDependency,
    settings: SettingsDependency,
    database: DatabaseDependency,
) -> User:
    token = request.cookies.get(settings.auth_session_cookie_name)
    current = await auth.current_session(token)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="login required or session expired",
        )
    if current.rotated_token is not None:
        response.set_cookie(
            key=settings.auth_session_cookie_name,
            value=current.rotated_token,
            max_age=settings.auth_session_ttl_seconds,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
    async with database.session_factory() as session:
        user = (
            await session.scalars(
                select(User).where(User.student_number == current.student_number).limit(1)
            )
        ).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="account not found")
    return user


CurrentUserDependency = Annotated[User, Depends(require_current_user)]


async def optional_current_user(
    request: Request,
    response: Response,
    auth: AuthServiceDependency,
    settings: SettingsDependency,
    database: DatabaseDependency,
) -> User | None:
    token = request.cookies.get(settings.auth_session_cookie_name)
    if not token:
        return None
    current = await auth.current_session(token)
    if current is None:
        response.delete_cookie(
            key=settings.auth_session_cookie_name,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
        return None
    if current.rotated_token is not None:
        response.set_cookie(
            key=settings.auth_session_cookie_name,
            value=current.rotated_token,
            max_age=settings.auth_session_ttl_seconds,
            path="/",
            secure=True,
            httponly=True,
            samesite="lax",
        )
    async with database.session_factory() as session:
        return (
            await session.scalars(
                select(User).where(User.student_number == current.student_number).limit(1)
            )
        ).one_or_none()


OptionalUserDependency = Annotated[User | None, Depends(optional_current_user)]
