from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from timetabler.api.dependencies import CatalogDependency
from timetabler.catalog.models import CatalogPage, Semester

router = APIRouter(tags=["catalog"])


@router.get("/semesters", response_model=tuple[Semester, ...])
async def semesters(catalog: CatalogDependency) -> tuple[Semester, ...]:
    return catalog.semesters()


@router.get("/catalog/{semester}", response_model=CatalogPage)
async def catalog_page(
    semester: str,
    catalog: CatalogDependency,
    q: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=200)] = None,
    course_code: Annotated[str | None, Query(max_length=40)] = None,
    professor: Annotated[str | None, Query(max_length=100)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=2000)] = 2000,
) -> CatalogPage:
    try:
        return catalog.query(
            semester,
            q=q,
            category=category,
            course_code=course_code,
            professor=professor,
            offset=offset,
            limit=limit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="semester not found") from exc
