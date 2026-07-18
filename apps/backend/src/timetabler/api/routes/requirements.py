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
from timetabler.db.models import (
    CompletedCourse,
    CurriculumProgramAlias,
    CurriculumProgramRequirement,
    CurriculumRequiredCourse,
    GraduationRequirementRule,
)
from timetabler.requirements.normalizer import academic_unit_key
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
    return not (unit and unit != "GENERAL_EXCEPTIONS_EXCLUDED" and unit != profile.department_id)


def _filtered(payload: dict[str, Any], profile: RequirementProfile) -> tuple[dict[str, Any], ...]:
    return tuple(rule for rule in payload.get("rules", []) if _applies(rule, profile))


def _static_major_requirements(
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


async def _major_requirements(
    database: DatabaseDependency,
    settings: SettingsDependency,
    profile: RequirementProfile,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    async with database.session_factory() as session:
        programs = list(
            (
                await session.scalars(
                    select(CurriculumProgramRequirement)
                    .join(
                        CurriculumProgramAlias,
                        CurriculumProgramAlias.program_id == CurriculumProgramRequirement.id,
                    )
                    .where(
                        CurriculumProgramAlias.admission_year == profile.admission_year,
                        CurriculumProgramAlias.alias_key
                        == academic_unit_key(profile.department_id),
                    )
                    .limit(2)
                )
            ).all()
        )
        if len(programs) == 1:
            program = programs[0]
            courses = list(
                (
                    await session.scalars(
                        select(CurriculumRequiredCourse)
                        .where(
                            CurriculumRequiredCourse.program_id == program.id,
                            CurriculumRequiredCourse.classification == "전필",
                        )
                        .order_by(
                            CurriculumRequiredCourse.grade.asc(),
                            CurriculumRequiredCourse.course_code.asc(),
                        )
                    )
                ).all()
            )
            return tuple(course.course_name for course in courses), ()
        if len(programs) > 1:
            return (), ("동일 학과명으로 여러 교육과정이 확인되어 별도 검토가 필요합니다.",)
    if profile.admission_year == 2026:
        return _static_major_requirements(settings, profile)
    return (), (f"{profile.admission_year}학번 학과 교육과정 매핑을 확인할 수 없습니다.",)


async def _database_rules(
    database: DatabaseDependency,
    profile: RequirementProfile,
) -> tuple[dict[str, Any], ...]:
    requested_key = academic_unit_key(profile.department_id)
    async with database.session_factory() as session:
        canonical_keys = {requested_key}
        program_keys = list(
            await session.scalars(
                select(CurriculumProgramRequirement.academic_unit_key)
                .join(
                    CurriculumProgramAlias,
                    CurriculumProgramAlias.program_id == CurriculumProgramRequirement.id,
                )
                .where(
                    CurriculumProgramAlias.admission_year == profile.admission_year,
                    CurriculumProgramAlias.alias_key == requested_key,
                )
            )
        )
        canonical_keys.update(program_keys)
        rows = list(
            await session.scalars(
                select(GraduationRequirementRule).where(
                    GraduationRequirementRule.rule_kind.in_(
                        (
                            "DEGREE_CREDIT_PROFILE",
                            "DEPARTMENT_ASSESSMENT_PROFILE",
                            "LEGACY_DEPARTMENT_ASSESSMENT",
                        )
                    ),
                    GraduationRequirementRule.academic_unit_key.in_(canonical_keys),
                )
            )
        )
    applicable: list[dict[str, Any]] = []
    for row in rows:
        if row.student_type and row.student_type != profile.student_type:
            continue
        if row.rule_kind == "DEGREE_CREDIT_PROFILE" and (
            row.admission_year_start != profile.admission_year
            or row.admission_year_end != profile.admission_year
            or row.program_path != profile.program_path
        ):
            continue
        applicable.append(row.raw_payload)
    return tuple(
        sorted(
            applicable,
            key=lambda rule: (
                rule.get("kind") != "DEGREE_CREDIT_PROFILE",
                str(rule.get("id", "")),
            ),
        )
    )


def _combined_rules(
    common: tuple[dict[str, Any], ...],
    database_rules: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    if not any(rule.get("kind") == "DEGREE_CREDIT_PROFILE" for rule in database_rules):
        return (*common, *database_rules)
    replaced_kinds = {
        "TOTAL_CREDITS",
        "LIBERAL_TOTAL",
        "REQUIRED_COURSE_GROUP",
        "PRIMARY_MAJOR_CREDITS",
        "MAJOR_CREDIT_PAIR",
        "ACADEMIC_UNIT_OVERRIDE",
    }
    return (
        *(rule for rule in common if rule.get("kind") not in replaced_kinds),
        *database_rules,
    )


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
    course_codes = {item.course_code for item in courses if item.course_code}
    categories: dict[str, float] = {}
    for item in courses:
        key = academic_unit_key(item.category)
        categories[key] = categories.get(key, 0) + item.credits
    credit_status: list[RequirementStatus] = []
    course_status: list[RequirementStatus] = []
    missing: list[str] = []
    manual: list[str] = []
    area_requirements: list[dict[str, Any]] = []

    def category_credits(*keys: str) -> float:
        normalized_keys = {academic_unit_key(key) for key in keys}
        return sum(
            credits for category, credits in categories.items() if category in normalized_keys
        )

    def add_credit_status(kind: str, required: float | None, current: float) -> None:
        satisfied = current >= required if required is not None else None
        credit_status.append(
            RequirementStatus(
                kind=kind,
                required=required,
                current=round(current, 2),
                satisfied=satisfied,
            )
        )
        if satisfied is False:
            assert required is not None
            missing.append(f"{kind}: {round(required - current, 2)}학점 부족")

    def add_required_courses(kind: str, required: list[dict[str, Any]]) -> None:
        missing_courses = tuple(
            str(item["name"])
            for item in required
            if not (
                item.get("courseCode") in course_codes
                or normalize_search_text(str(item["name"])) in names
                or any(
                    normalize_search_text(str(alias)) in names for alias in item.get("aliases", [])
                )
            )
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

    for rule in rules:
        kind = str(rule.get("kind"))
        minimum = float(rule["min"]) if rule.get("min") is not None else None
        current = {
            "TOTAL_CREDITS": total,
            "LIBERAL_TOTAL": liberal,
            "PRIMARY_MAJOR_CREDITS": major,
        }.get(kind)
        if current is not None:
            add_credit_status(kind, minimum, current)
        elif kind == "REQUIRED_COURSE_GROUP":
            add_required_courses(kind, list(rule.get("courses", [])))
        elif kind == "DEGREE_CREDIT_PROFILE":
            values = rule.get("values", {})
            profile_metrics = (
                ("TOTAL_CREDITS", values.get("totalCreditsMin"), total),
                (
                    "LIBERAL_REQUIRED_CREDITS",
                    values.get("liberalRequiredMin"),
                    category_credits("교양필수", "교필"),
                ),
                (
                    "LIBERAL_ELECTIVE_CREDITS",
                    values.get("liberalElectiveMin"),
                    category_credits("교양선택", "교선"),
                ),
                ("LIBERAL_TOTAL", values.get("liberalMin"), liberal),
                (
                    "MAJOR_FOUNDATION_CREDITS",
                    values.get("majorFoundationMin"),
                    category_credits("전공기초", "전기"),
                ),
                (
                    "MAJOR_REQUIRED_CREDITS",
                    values.get("majorRequiredMin"),
                    category_credits("전공필수", "전필"),
                ),
                (
                    "MAJOR_ELECTIVE_CREDITS",
                    values.get("majorElectiveMin"),
                    category_credits("전공선택", "전선"),
                ),
                ("PRIMARY_MAJOR_CREDITS", values.get("primaryMajorMin"), major),
            )
            for metric_kind, required, metric_current in profile_metrics:
                add_credit_status(
                    metric_kind,
                    float(required) if required is not None else None,
                    metric_current,
                )
            required_liberal = list(rule.get("requiredLiberalCourses", []))
            if required_liberal:
                add_required_courses("LIBERAL_REQUIRED_COURSES", required_liberal)
            area_requirements = list(rule.get("liberalAreaRequirements", []))
            if values.get("secondaryProgramMin"):
                manual.append("SECONDARY_PROGRAM_CREDITS")
            if rule.get("consistencyWarnings"):
                manual.append("SOURCE_CREDIT_TABLE_CONSISTENCY")
        elif kind in {
            "DEPARTMENT_ASSESSMENT_PROFILE",
            "LEGACY_DEPARTMENT_ASSESSMENT",
        }:
            manual.append(kind)
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
    if not area_requirements and any(
        rule.get("kind") == "LIBERAL_TOTAL" and rule.get("components", {}).get("areaCount")
        for rule in rules
    ):
        area_requirements = [{"area": area, "minCredits": 2, "minCourses": 1} for area in _AREAS]
    area_status = tuple(
        AreaStatus(
            area=str(requirement["area"]),
            credits=round(
                sum(item.credits for item in courses if (item.area or "") == requirement["area"]),
                2,
            ),
            satisfied=(
                sum(item.credits for item in courses if (item.area or "") == requirement["area"])
                >= float(requirement.get("minCredits") or 0)
                and sum(1 for item in courses if (item.area or "") == requirement["area"])
                >= int(requirement.get("minCourses") or 0)
            ),
        )
        for requirement in area_requirements
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
    database: DatabaseDependency,
    admission_year: int = Query(alias="admissionYear", ge=1990, le=2100),
    department_id: str = Query(alias="departmentId"),
    student_type: str = Query(alias="studentType"),
    program_path: str = Query(alias="programPath"),
) -> RequirementRuleList:
    payload = _rules(settings)
    profile = _profile(admission_year, department_id, student_type, program_path)
    database_rules = await _database_rules(database, profile)
    rules = _combined_rules(_filtered(payload, profile), database_rules)
    return RequirementRuleList(
        rules=rules,
        manual_review_items=tuple(
            dict.fromkeys(
                [
                    *payload.get("manualReviewReasons", []),
                    *(
                        str(rule["kind"])
                        for rule in database_rules
                        if rule.get("requiresManualReview")
                    ),
                ]
            )
        ),
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
    database_rules = await _database_rules(database, body)
    major_required, major_manual = await _major_requirements(database, settings, body)
    return _evaluate_rules(
        _combined_rules(_filtered(payload, body), database_rules),
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
    database_rules = await _database_rules(database, profile)
    major_required, major_manual = await _major_requirements(database, settings, profile)
    evaluation = _evaluate_rules(
        _combined_rules(_filtered(payload, profile), database_rules),
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
