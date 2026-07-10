from __future__ import annotations

import json
import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from timetabler import __version__
from timetabler.api.routes import catalog, health, optimizations
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import Settings, get_settings
from timetabler.db.session import Database
from timetabler.jobs.store import OptimizationJobStore

logger = logging.getLogger("timetabler.api")


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        catalog_repository = CatalogRepository(
            resolved.data_root,
            validate_checksums=resolved.catalog_validate_checksums,
        )
        _ = catalog_repository.snapshot
        database = Database(resolved.database_url)
        if resolved.auto_create_schema:
            await database.create_schema()
        app.state.catalog = catalog_repository
        app.state.database = database
        app.state.job_store = OptimizationJobStore(database.session_factory)
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        title="PL-timeTabler API",
        version=__version__,
        openapi_version="3.1.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed method=%s path=%s status=%s duration_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            (time.monotonic() - started) * 1000,
            request_id,
        )
        return response

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(optimizations.router, prefix="/api/v1")
    app.include_router(optimizations.alias_router, prefix="/api/v1")

    @app.get("/api/v1/requirements/common", include_in_schema=False)
    async def common_requirements() -> dict:
        path = resolved.data_root / "requirements" / "normalized" / "common-graduation-rules.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="requirements data not found")
        return json.loads(path.read_text(encoding="utf-8"))

    return app


app = create_app()
