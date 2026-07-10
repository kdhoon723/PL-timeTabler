from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

from timetabler.api.dependencies import CatalogDependency, DatabaseDependency
from timetabler.api.schemas import HealthStatus, ReadinessStatus

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthStatus)
async def live() -> HealthStatus:
    return HealthStatus(status="live")


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    responses={503: {"model": ReadinessStatus}},
)
async def ready(
    catalog: CatalogDependency,
    database: DatabaseDependency,
) -> ReadinessStatus | ORJSONResponse:
    try:
        _ = catalog.snapshot
        catalog_status = "ready"
    except Exception:
        catalog_status = "unavailable"
    try:
        await database.ping()
        database_status = "ready"
    except Exception:
        database_status = "unavailable"
    status = "ready" if catalog_status == database_status == "ready" else "not_ready"
    payload = ReadinessStatus(
        status=status,
        catalog=catalog_status,
        database=database_status,
    )
    if status != "ready":
        return ORJSONResponse(
            status_code=503,
            content=payload.model_dump(mode="json", by_alias=True),
        )
    return payload
