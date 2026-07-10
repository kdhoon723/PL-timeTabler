from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from timetabler.catalog.repository import CatalogRepository
from timetabler.db.session import Database
from timetabler.jobs.store import OptimizationJobStore


def get_catalog(request: Request) -> CatalogRepository:
    return request.app.state.catalog


def get_database(request: Request) -> Database:
    return request.app.state.database


def get_job_store(request: Request) -> OptimizationJobStore:
    return request.app.state.job_store


CatalogDependency = Annotated[CatalogRepository, Depends(get_catalog)]
DatabaseDependency = Annotated[Database, Depends(get_database)]
JobStoreDependency = Annotated[OptimizationJobStore, Depends(get_job_store)]
