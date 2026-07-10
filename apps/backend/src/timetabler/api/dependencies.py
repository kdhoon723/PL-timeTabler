from __future__ import annotations

from typing import Annotated, cast

from fastapi import Depends, Request

from timetabler.api.rate_limit import SlidingWindowRateLimiter
from timetabler.auth.service import AuthService
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import Settings
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
