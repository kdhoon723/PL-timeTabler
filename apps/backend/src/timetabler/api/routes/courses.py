from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from timetabler.api.dependencies import (
    CatalogDependency,
    DatabaseDependency,
    OptionalUserDependency,
    SettingsDependency,
)
from timetabler.api.resource_schemas import (
    CourseDetailRead,
    CourseListRead,
    CourseSummaryRead,
    DepartmentListRead,
    DepartmentRead,
    RatingSummary,
)
from timetabler.catalog.models import Section
from timetabler.db.models import CourseReview, SavedTimetable
from timetabler.types import normalize_search_text

course_router = APIRouter(prefix="/courses", tags=["courses"])
section_router = APIRouter(prefix="/sections", tags=["courses"])
department_router = APIRouter(prefix="/departments", tags=["departments"])


def _popularity(average: float, count: int) -> float:
    return round(average * math.log2(count + 1), 3) if count else 0.0


def _grade_map(data_root: Path) -> dict[str, int]:
    path = data_root / "requirements" / "normalized" / "major-required-courses-2026.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    result: dict[str, int] = {}
    for program in payload.get("programs", []):
        for course in program.get("courses", []):
            if course.get("grade") is not None:
                result[str(course["courseCode"])] = int(course["grade"])
    return result


async def _ratings(database: DatabaseDependency) -> dict[str, tuple[float, int]]:
    async with database.session_factory() as session:
        rows = (
            await session.execute(
                select(
                    CourseReview.course_code,
                    func.avg(CourseReview.rating),
                    func.count(CourseReview.id),
                ).group_by(CourseReview.course_code)
            )
        ).all()
    return {str(code): (round(float(average or 0), 2), int(count)) for code, average, count in rows}


def _summaries(
    sections: tuple[Section, ...] | list[Section],
    grades: dict[str, int],
    ratings: dict[str, tuple[float, int]],
) -> list[CourseSummaryRead]:
    groups: dict[str, list[Section]] = defaultdict(list)
    for section in sections:
        groups[section.course_code].append(section)
    result: list[CourseSummaryRead] = []
    for code, group in groups.items():
        first = group[0]
        average, count = ratings.get(code, (0.0, 0))
        result.append(
            CourseSummaryRead(
                course_code=code,
                name=first.name,
                category=first.category,
                credits=first.credits,
                grade=grades.get(code),
                section_count=len(group),
                professors=tuple(sorted({item.professor for item in group if item.professor})),
                average_rating=average,
                review_count=count,
                popularity_score=_popularity(average, count),
            )
        )
    return result


@course_router.get("", response_model=CourseListRead)
async def list_courses(
    catalog: CatalogDependency,
    database: DatabaseDependency,
    settings: SettingsDependency,
    semester: str = "2026-1",
    keyword: str | None = None,
    professor: str | None = None,
    department_id: str | None = Query(default=None, alias="departmentId"),
    category: str | None = None,
    area: str | None = None,
    grade: int | None = Query(default=None, ge=1, le=4),
    day: str | None = Query(default=None, pattern="^[월화수목금토일]$"),
    sort: str = Query(default="NAME", pattern="^(NAME|POPULARITY|RATING|REVIEWS)$"),
    order: str = Query(default="ASC", pattern="^(ASC|DESC)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=2000),
) -> CourseListRead:
    if semester != catalog.snapshot.semester:
        raise HTTPException(status_code=404, detail="semester not found")
    grades = _grade_map(settings.data_root)
    needle = normalize_search_text(keyword) if keyword else None
    professor_needle = normalize_search_text(professor) if professor else None
    matched = []
    for section in catalog.snapshot.sections:
        if needle and needle not in normalize_search_text(
            f"{section.course_code} {section.name} {section.professor or ''}"
        ):
            continue
        if professor_needle and professor_needle not in normalize_search_text(
            section.professor or ""
        ):
            continue
        if department_id and department_id not in section.category:
            continue
        if category and section.category != category:
            continue
        if area and area not in section.category:
            continue
        if grade is not None and grades.get(section.course_code) != grade:
            continue
        if day and not any(meeting.day == day for meeting in section.sessions):
            continue
        matched.append(section)
    courses = _summaries(matched, grades, await _ratings(database))
    reverse = order == "DESC"
    key = {
        "NAME": lambda item: (item.name, item.course_code),
        "POPULARITY": lambda item: (item.popularity_score, item.review_count, item.name),
        "RATING": lambda item: (item.average_rating, item.review_count, item.name),
        "REVIEWS": lambda item: (item.review_count, item.average_rating, item.name),
    }[sort]
    courses.sort(key=key, reverse=reverse)
    start = (page - 1) * size
    return CourseListRead(
        courses=tuple(courses[start : start + size]),
        page=page,
        size=size,
        total=len(courses),
    )


@course_router.get("/{course_code}", response_model=CourseDetailRead)
async def get_course(
    course_code: str,
    catalog: CatalogDependency,
    database: DatabaseDependency,
    settings: SettingsDependency,
    semester: str = "2026-1",
) -> CourseDetailRead:
    if semester != catalog.snapshot.semester:
        raise HTTPException(status_code=404, detail="semester not found")
    sections = tuple(
        section for section in catalog.snapshot.sections if section.course_code == course_code
    )
    if not sections:
        raise HTTPException(status_code=404, detail="course not found")
    ratings = await _ratings(database)
    summary = _summaries(sections, _grade_map(settings.data_root), ratings)[0]
    return CourseDetailRead(
        course=summary,
        sections=sections,
        rating_summary=RatingSummary(
            average_rating=summary.average_rating,
            review_count=summary.review_count,
            popularity_score=summary.popularity_score,
        ),
    )


@course_router.get("/{course_code}/sections", response_model=tuple[Section, ...])
async def list_course_sections(
    course_code: str,
    catalog: CatalogDependency,
    semester: str = "2026-1",
    professor: str | None = None,
    day: str | None = Query(default=None, pattern="^[월화수목금토일]$"),
) -> tuple[Section, ...]:
    if semester != catalog.snapshot.semester:
        raise HTTPException(status_code=404, detail="semester not found")
    sections = tuple(
        section
        for section in catalog.snapshot.sections
        if section.course_code == course_code
        and (professor is None or section.professor == professor)
        and (day is None or any(meeting.day == day for meeting in section.sessions))
    )
    if not sections:
        raise HTTPException(status_code=404, detail="course sections not found")
    return sections


@section_router.get("/{section_id}", response_model=Section)
async def get_section(section_id: str, catalog: CatalogDependency) -> Section:
    section = catalog.by_id(catalog.snapshot.semester).get(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="section not found")
    return section


@section_router.get("/{section_id}/alternatives", response_model=tuple[Section, ...])
async def get_alternatives(
    section_id: str,
    catalog: CatalogDependency,
    database: DatabaseDependency,
    user: OptionalUserDependency,
    same_professor: bool = Query(default=False, alias="sameProfessor"),
    timetable_id: str | None = Query(default=None, alias="timetableId"),
) -> tuple[Section, ...]:
    section = catalog.by_id(catalog.snapshot.semester).get(section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="section not found")
    comparison_sections: tuple[Section, ...] = ()
    if timetable_id is not None:
        if user is None:
            raise HTTPException(status_code=401, detail="login required")
        async with database.session_factory() as session:
            timetable = await session.get(SavedTimetable, timetable_id)
        if timetable is None:
            raise HTTPException(status_code=404, detail="timetable not found")
        if timetable.user_id != user.id:
            raise HTTPException(status_code=403, detail="timetable access denied")
        by_id = catalog.by_id(timetable.semester)
        comparison_sections = tuple(
            by_id[item["sectionId"]]
            for item in timetable.items_snapshot
            if item.get("role") in {"must", "want"}
            and item.get("sectionId") != section_id
            and item.get("sectionId") in by_id
        )

    def conflicts(candidate: Section) -> bool:
        return any(
            left.day == right.day
            and left.start_minute < right.end_minute
            and right.start_minute < left.end_minute
            for other in comparison_sections
            for left in candidate.sessions
            for right in other.sessions
        )

    return tuple(
        candidate
        for candidate in catalog.snapshot.sections
        if candidate.course_code == section.course_code
        and candidate.id != section.id
        and (not same_professor or candidate.professor == section.professor)
        and not conflicts(candidate)
    )


def _departments(data_root: Path) -> tuple[DepartmentRead, ...]:
    path = data_root / "requirements" / "normalized" / "department-sources-2026.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="department data unavailable") from exc
    return tuple(
        DepartmentRead(
            id=str(item["academicUnit"]),
            college=str(item["college"]),
            name=str(item["academicUnit"]),
            curriculum_url=item.get("curriculumUrl"),
            graduation_url=item.get("graduationUrl"),
        )
        for item in payload.get("departments", [])
    )


@department_router.get("", response_model=DepartmentListRead)
async def list_departments(
    settings: SettingsDependency,
    keyword: str | None = None,
) -> DepartmentListRead:
    departments = _departments(settings.data_root)
    if keyword:
        needle = normalize_search_text(keyword)
        departments = tuple(
            item
            for item in departments
            if needle in normalize_search_text(f"{item.name} {item.college}")
        )
    return DepartmentListRead(departments=departments)


@department_router.get("/{department_id}", response_model=DepartmentRead)
async def get_department(
    department_id: str,
    settings: SettingsDependency,
) -> DepartmentRead:
    department = next(
        (item for item in _departments(settings.data_root) if item.id == department_id), None
    )
    if department is None:
        raise HTTPException(status_code=404, detail="department not found")
    return department
