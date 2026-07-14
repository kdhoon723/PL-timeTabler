from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from timetabler.api.dependencies import (
    CatalogDependency,
    CurrentUserDependency,
    DatabaseDependency,
    SettingsDependency,
)
from timetabler.api.resource_schemas import (
    AreaStatus,
    CourseSummaryRead,
    RequirementEvaluation,
    RequirementProfile,
    RequirementRecommendation,
    RequirementRuleList,
    RequirementSource,
    RequirementStatus,
)
from timetabler.db.models import CompletedCourse
from timetabler.types import normalize_search_text

router = APIRouter(prefix="/requirements", tags=["requirements"])
_GENERAL_EXCEPTION_UNITS = {"간호학과"}
_AREAS = (
    "제1영역:인간과소통",
    "제2영역:사회와경제",
    "제3영역:과학과기술",
    "제4영역:예술과문화",
    "제5영역:융합과혁신",
    "제6영역:AI·디지털리터러시",
)
_SOURCE_ALIASES = {
    "regulations-2-1-01": "academic_regulations_2_1_01",
    "regulations-2-1-02": "academic_regulations_enforcement_2_1_02",
    "curriculum-guide-2026": "curriculum_handbook_post_2026",
}


def _json(path: Any) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise TypeError
        return value
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail="requirement data unavailable") from exc


def _rules(settings: SettingsDependency) -> dict[str, Any]:
    return _json(
        settings.data_root / "requirements" / "normalized" / "common-graduation-rules.json"
    )


def _applies(rule: dict[str, Any], profile: RequirementProfile) -> bool:
    years = rule.get("admissionYears", {})
    if years.get("start") and profile.admission_year < int(years["start"]):
        return False
    if years.get("end") and profile.admission_year > int(years["end"]):
        return False
    scope = rule.get("scope", {})
    if scope.get("studentType") == "DOMESTIC" and profile.student_type != "DOMESTIC":
        return False
    if scope.get("programPath") and scope["programPath"] != profile.program_path:
        return False
    unit = scope.get("academicUnit")
    if unit == "GENERAL_EXCEPTIONS_EXCLUDED" and profile.department_id in _GENERAL_EXCEPTION_UNITS:
        return False
    return not (
        unit and unit != "GENERAL_EXCEPTIONS_EXCLUDED" and unit != profile.department_id
    )


def _filtered(payload: dict[str, Any], profile: RequirementProfile) -> tuple[dict[str, Any], ...]:
    return tuple(rule for rule in payload.get("rules", []) if _applies(rule, profile))


def _major_requirements(
    settings: SettingsDependency,
    profile: RequirementProfile,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    payload = _json(
        settings.data_root / "requirements" / "normalized" / "major-required-courses-2026.json"
    )
    cohort = int(payload.get("cohortAdmissionYear", 0))
    if profile.admission_year != cohort:
        return (), (f"{profile.admission_year}학번 전공필수 자료는 별도 확인이 필요합니다.",)
    program = next(
        (
            item
            for item in payload.get("programs", [])
            if item.get("academicUnit") == profile.department_id
        ),
        None,
    )
    if program is None:
        return (), ("소속 학과 전공필수 자료를 확인할 수 없습니다.",)
    if program.get("status") != "AVAILABLE":
        return (), (str(program.get("manualReviewReason") or "전공필수 수동 확인 필요"),)
    return tuple(str(item["name"]) for item in program.get("courses", [])), ()


async def _completed(database: DatabaseDependency, user_id: str) -> list[CompletedCourse]:
    async with database.session_factory() as session:
        return list(
            (
                await session.scalars(
                    select(CompletedCourse).where(
                        CompletedCourse.user_id == user_id,
                        CompletedCourse.status == "COMPLETED",
                    )
                )
            ).all()
        )


def _profile(
    admission_year: int,
    department_id: str,
    student_type: str,
    program_path: str,
) -> RequirementProfile:
    return RequirementProfile(
        admission_year=admission_year,
        department_id=department_id,
        student_type=student_type,
        program_path=program_path,
    )


def _evaluate_rules(
    rules: tuple[dict[str, Any], ...],
    courses: list[CompletedCourse],
    manual_reasons: tuple[str, ...],
    major_required: tuple[str, ...] = (),
) -> RequirementEvaluation:
    total = sum(item.credits for item in courses)
    major = sum(item.credits for item in courses if item.category.startswith("전공"))
    liberal = sum(item.credits for item in courses if item.category.startswith("교양"))
    names = {normalize_search_text(item.course_name) for item in courses}
    areas = {
        area: round(
            sum(item.credits for item in courses if (item.area or "") == area), 2
        )
        for area in _AREAS
    }
    credit_status: list[RequirementStatus] = []
    course_status: list[RequirementStatus] = []
    missing: list[str] = []
    manual: list[str] = []
    for rule in rules:
        kind = str(rule.get("kind"))
        minimum = float(rule["min"]) if rule.get("min") is not None else None
        current = {
            "TOTAL_CREDITS": total,
            "LIBERAL_TOTAL": liberal,
            "PRIMARY_MAJOR_CREDITS": major,
        }.get(kind)
        if current is not None:
            satisfied = current >= minimum if minimum is not None else None
            credit_status.append(
                RequirementStatus(
                    kind=kind,
                    required=minimum,
                    current=round(current, 2),
                    satisfied=satisfied,
                )
            )
            if satisfied is False:
                assert minimum is not None
                missing.append(f"{kind}: {round(minimum - current, 2)}학점 부족")
        elif kind == "REQUIRED_COURSE_GROUP":
            required = [str(item["name"]) for item in rule.get("courses", [])]
            missing_courses = tuple(
                name for name in required if normalize_search_text(name) not in names
            )
            course_status.append(
                RequirementStatus(
                    kind=kind,
                    required=float(len(required)),
                    current=float(len(required) - len(missing_courses)),
                    satisfied=not missing_courses,
                    missing=missing_courses,
                )
            )
            missing.extend(f"필수과목: {name}" for name in missing_courses)
        else:
            manual.append(kind)
        if rule.get("requiresManualReview") and kind not in manual:
            manual.append(kind)
    if major_required:
        missing_major = tuple(
            name for name in major_required if normalize_search_text(name) not in names
        )
        course_status.append(
            RequirementStatus(
                kind="MAJOR_REQUIRED_COURSES",
                required=float(len(major_required)),
                current=float(len(major_required) - len(missing_major)),
                satisfied=not missing_major,
                missing=missing_major,
            )
        )
        missing.extend(f"전공필수: {name}" for name in missing_major)
    area_status = tuple(
        AreaStatus(area=area, credits=credit, satisfied=credit >= 2)
        for area, credit in areas.items()
    )
    missing.extend(f"교양영역: {item.area}" for item in area_status if not item.satisfied)
    return RequirementEvaluation(
        credit_status=tuple(credit_status),
        area_status=area_status,
        required_course_status=tuple(course_status),
        missing_requirements=tuple(missing),
        manual_review_items=tuple(dict.fromkeys([*manual, *manual_reasons])),
    )


@router.get("/common")
async def common_rules(settings: SettingsDependency) -> dict[str, Any]:
    return _rules(settings)


@router.get("/rules", response_model=RequirementRuleList)
async def list_requirement_rules(
    settings: SettingsDependency,
    admission_year: int = Query(alias="admissionYear", ge=1990, le=2100),
    department_id: str = Query(alias="departmentId"),
    student_type: str = Query(alias="studentType"),
    program_path: str = Query(alias="programPath"),
) -> RequirementRuleList:
    payload = _rules(settings)
    profile = _profile(admission_year, department_id, student_type, program_path)
    return RequirementRuleList(
        rules=_filtered(payload, profile),
        manual_review_items=tuple(payload.get("manualReviewReasons", [])),
        as_of=str(payload.get("asOf", "")),
    )


@router.post("/evaluate", response_model=RequirementEvaluation)
async def evaluate_requirements(
    body: RequirementProfile,
    user: CurrentUserDependency,
    database: DatabaseDependency,
    settings: SettingsDependency,
) -> RequirementEvaluation:
    payload = _rules(settings)
    major_required, major_manual = _major_requirements(settings, body)
    return _evaluate_rules(
        _filtered(payload, body),
        await _completed(database, user.id),
        (*tuple(payload.get("manualReviewReasons", [])), *major_manual),
        major_required,
    )


@router.get("/recommendations", response_model=RequirementRecommendation)
async def requirement_recommendations(
    user: CurrentUserDependency,
    database: DatabaseDependency,
    settings: SettingsDependency,
    catalog: CatalogDependency,
    semester: str = "2026-1",
    admission_year: int = Query(alias="admissionYear", ge=1990, le=2100),
    department_id: str = Query(alias="departmentId"),
    student_type: str = Query(alias="studentType"),
    program_path: str = Query(alias="programPath"),
) -> RequirementRecommendation:
    if semester != catalog.snapshot.semester:
        raise HTTPException(status_code=404, detail="semester not found")
    payload = _rules(settings)
    profile = _profile(admission_year, department_id, student_type, program_path)
    courses = await _completed(database, user.id)
    major_required, major_manual = _major_requirements(settings, profile)
    evaluation = _evaluate_rules(
        _filtered(payload, profile),
        courses,
        (*tuple(payload.get("manualReviewReasons", [])), *major_manual),
        major_required,
    )
    missing_names = {
        item.removeprefix("필수과목: ").removeprefix("전공필수: ")
        for item in evaluation.missing_requirements
        if item.startswith(("필수과목: ", "전공필수: "))
    }
    recommendations: list[CourseSummaryRead] = []
    for name in sorted(missing_names):
        normalized = normalize_search_text(name)
        group = [
            section
            for section in catalog.snapshot.sections
            if normalized in normalize_search_text(section.name)
        ]
        if not group:
            continue
        first = group[0]
        recommendations.append(
            CourseSummaryRead(
                course_code=first.course_code,
                name=first.name,
                category=first.category,
                credits=first.credits,
                grade=None,
                section_count=len(group),
                professors=tuple(sorted({item.professor for item in group if item.professor})),
                average_rating=0,
                review_count=0,
                popularity_score=0,
            )
        )
    return RequirementRecommendation(
        missing_requirements=evaluation.missing_requirements,
        recommended_courses=tuple(recommendations),
    )


@router.get("/sources/{source_id}", response_model=RequirementSource)
async def get_requirement_source(
    source_id: str,
    settings: SettingsDependency,
) -> RequirementSource:
    payload = _json(settings.data_root / "requirements" / "normalized" / "sources.json")
    sources = payload.get("official_sources", {})
    key = _SOURCE_ALIASES.get(source_id, source_id)
    url = sources.get(key)
    if not isinstance(url, str):
        raise HTTPException(status_code=404, detail="requirement source not found")
    return RequirementSource(
        source_id=source_id,
        title=source_id.replace("-", " "),
        url=url,
        effective_date=None,
        verified_at=str(payload.get("as_of", "")),
    )
