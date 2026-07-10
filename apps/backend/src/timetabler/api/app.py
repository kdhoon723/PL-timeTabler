from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from timetabler import __version__
from timetabler.api.rate_limit import SlidingWindowRateLimiter
from timetabler.api.routes import auth, catalog, health, optimizations
from timetabler.auth.mailer import OtpMailer, build_otp_mailer
from timetabler.auth.service import AuthService
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import Settings, get_settings
from timetabler.db.session import Database
from timetabler.jobs.store import OptimizationJobStore

logger = logging.getLogger("timetabler.api")


def create_app(
    settings: Settings | None = None,
    *,
    otp_mailer: OtpMailer | None = None,
) -> FastAPI:
    resolved = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved.validate_auth_configuration(external_mailer=otp_mailer is not None)
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
        app.state.settings = resolved
        app.state.optimization_rate_limiter = SlidingWindowRateLimiter(
            limit=resolved.optimization_rate_limit_requests,
            window_seconds=resolved.optimization_rate_limit_window_seconds,
        )
        app.state.auth_service = AuthService(
            database.session_factory,
            resolved,
            otp_mailer or build_otp_mailer(resolved),
        )
        try:
            yield
        finally:
            await database.close()

    app = FastAPI(
        title="PL-timeTabler API",
        version=__version__,
        openapi_version="3.1.0",
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
        if request.url.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "no-store, private"
            response.headers["Pragma"] = "no-cache"
            vary = response.headers.get("Vary")
            response.headers["Vary"] = f"{vary}, Cookie" if vary else "Cookie"
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
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(catalog.router, prefix="/api/v1")
    app.include_router(optimizations.router, prefix="/api/v1")
    return app


app = create_app()
