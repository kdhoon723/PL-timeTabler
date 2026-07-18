from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from timetabler.db.models import (
    CurriculumProgramAlias,
    CurriculumProgramRequirement,
    GraduationAssessmentCategory,
    GraduationAssessmentCredential,
    GraduationAssessmentProfile,
    GraduationAssessmentSourceReference,
    GraduationCreditProfile,
    GraduationCreditProfileAcademicUnitAlias,
    GraduationCreditProfileSourceReference,
    GraduationCreditProfileWarning,
    GraduationLegacyCohort,
    GraduationLegacyRequirement,
    GraduationLegacySourceReference,
    GraduationLiberalAreaRequirement,
    GraduationLiberalCourseAlias,
    GraduationLiberalCourseTerm,
    GraduationLiberalRequiredCourse,
    GraduationLiberalRequirementSet,
)
from timetabler.requirements.normalizer import academic_unit_key


@dataclass(frozen=True, slots=True)
class GraduationRuleScope:
    admission_year: int
    academic_unit: str
    student_type: str
    program_path: str


def _policy(none: str | None, one: str | None, two: str | None = None) -> dict[str, Any]:
    return {"none": none, "one": one, "two": two}


def _nonempty_fields(row: object, fields: tuple[str, ...]) -> dict[str, str]:
    return {
        field: str(value)
        for field in fields
        if (value := getattr(row, field)) is not None and str(value).strip()
    }


async def _canonical_keys(
    session: AsyncSession,
    scope: GraduationRuleScope,
) -> set[str]:
    requested_key = academic_unit_key(scope.academic_unit)
    programs = list(
        await session.scalars(
            select(CurriculumProgramRequirement)
            .join(
                CurriculumProgramAlias,
                CurriculumProgramAlias.program_id == CurriculumProgramRequirement.id,
            )
            .where(
                CurriculumProgramAlias.admission_year == scope.admission_year,
                CurriculumProgramAlias.alias_key == requested_key,
            )
        )
    )
    canonical_keys = {requested_key, *(program.academic_unit_key for program in programs)}
    return canonical_keys


async def _credit_rules(
    session: AsyncSession,
    scope: GraduationRuleScope,
    canonical_keys: set[str],
) -> list[dict[str, Any]]:
    profiles = list(
        await session.scalars(
            select(GraduationCreditProfile)
            .where(
                GraduationCreditProfile.academic_unit_key.in_(canonical_keys),
                GraduationCreditProfile.admission_year == scope.admission_year,
                GraduationCreditProfile.student_type == scope.student_type,
                GraduationCreditProfile.program_path == scope.program_path,
            )
            .order_by(GraduationCreditProfile.source_rule_id.asc())
        )
    )
    if not profiles:
        return []
    profile_ids = [profile.id for profile in profiles]
    aliases_by_profile: dict[str, list[str]] = defaultdict(list)
    for profile_alias in await session.scalars(
        select(GraduationCreditProfileAcademicUnitAlias)
        .where(GraduationCreditProfileAcademicUnitAlias.profile_id.in_(profile_ids))
        .order_by(
            GraduationCreditProfileAcademicUnitAlias.profile_id.asc(),
            GraduationCreditProfileAcademicUnitAlias.position.asc(),
        )
    ):
        aliases_by_profile[profile_alias.profile_id].append(profile_alias.alias)
    source_refs_by_profile: dict[str, list[str]] = defaultdict(list)
    for source_ref in await session.scalars(
        select(GraduationCreditProfileSourceReference)
        .where(GraduationCreditProfileSourceReference.profile_id.in_(profile_ids))
        .order_by(
            GraduationCreditProfileSourceReference.profile_id.asc(),
            GraduationCreditProfileSourceReference.position.asc(),
        )
    ):
        source_refs_by_profile[source_ref.profile_id].append(source_ref.source_ref)
    set_ids = {profile.liberal_requirement_set_id for profile in profiles}
    sets = {
        item.id: item
        for item in await session.scalars(
            select(GraduationLiberalRequirementSet).where(
                GraduationLiberalRequirementSet.id.in_(set_ids)
            )
        )
    }
    courses = list(
        await session.scalars(
            select(GraduationLiberalRequiredCourse)
            .where(GraduationLiberalRequiredCourse.requirement_set_id.in_(set_ids))
            .order_by(
                GraduationLiberalRequiredCourse.requirement_set_id.asc(),
                GraduationLiberalRequiredCourse.position.asc(),
            )
        )
    )
    course_ids = [course.id for course in courses]
    aliases_by_course: dict[str, list[str]] = defaultdict(list)
    terms_by_course: dict[str, list[int]] = defaultdict(list)
    if course_ids:
        for course_alias in await session.scalars(
            select(GraduationLiberalCourseAlias)
            .where(GraduationLiberalCourseAlias.course_id.in_(course_ids))
            .order_by(
                GraduationLiberalCourseAlias.course_id.asc(),
                GraduationLiberalCourseAlias.position.asc(),
            )
        ):
            aliases_by_course[course_alias.course_id].append(course_alias.alias)
        for term in await session.scalars(
            select(GraduationLiberalCourseTerm)
            .where(GraduationLiberalCourseTerm.course_id.in_(course_ids))
            .order_by(
                GraduationLiberalCourseTerm.course_id.asc(),
                GraduationLiberalCourseTerm.semester.asc(),
            )
        ):
            terms_by_course[term.course_id].append(term.semester)
    courses_by_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for course in courses:
        courses_by_set[course.requirement_set_id].append(
            {
                "courseCode": course.course_code,
                "name": course.course_name,
                "aliases": aliases_by_course[course.id],
                "credits": course.credits,
                "grade": course.grade,
                "semesters": terms_by_course[course.id],
                "sourceLocator": {"page": course.source_page},
            }
        )
    areas_by_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for area in await session.scalars(
        select(GraduationLiberalAreaRequirement)
        .where(GraduationLiberalAreaRequirement.requirement_set_id.in_(set_ids))
        .order_by(
            GraduationLiberalAreaRequirement.requirement_set_id.asc(),
            GraduationLiberalAreaRequirement.position.asc(),
        )
    ):
        areas_by_set[area.requirement_set_id].append(
            {
                "area": area.area,
                "minCourses": area.min_courses,
                "minCredits": area.min_credits,
            }
        )
    warnings_by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for warning in await session.scalars(
        select(GraduationCreditProfileWarning)
        .where(GraduationCreditProfileWarning.profile_id.in_(profile_ids))
        .order_by(
            GraduationCreditProfileWarning.profile_id.asc(),
            GraduationCreditProfileWarning.position.asc(),
        )
    ):
        warnings_by_profile[warning.profile_id].append(
            {
                "code": warning.code,
                "calculated": warning.calculated,
                "printed": warning.printed,
            }
        )

    result: list[dict[str, Any]] = []
    for profile in profiles:
        liberal = sets[profile.liberal_requirement_set_id]
        values: dict[str, Any] = {
            "liberalRequiredMin": liberal.required_credits_min,
            "liberalElectiveMin": liberal.elective_credits_min,
            "majorFoundationMin": profile.major_foundation_min,
            "majorRequiredMin": profile.major_required_min,
            "majorElectiveMin": profile.major_elective_min,
            "primaryMajorMin": profile.primary_major_min,
            "totalCreditsMin": profile.total_credits_min,
            "liberalMin": liberal.total_credits_min,
            "liberalMax": liberal.total_credits_max,
        }
        if profile.additional_major_min is not None:
            values["additionalMajorMin"] = profile.additional_major_min
        if profile.secondary_program_min is not None:
            values["secondaryProgramMin"] = profile.secondary_program_min
        result.append(
            {
                "id": profile.source_rule_id,
                "admissionYears": {
                    "start": profile.admission_year,
                    "end": profile.admission_year,
                },
                "scope": {
                    "studentType": profile.student_type,
                    "academicUnit": profile.academic_unit,
                    "programPath": profile.program_path,
                },
                "kind": "DEGREE_CREDIT_PROFILE",
                "academicUnitAliases": aliases_by_profile[profile.id],
                "values": values,
                "requiredLiberalCourses": courses_by_set[liberal.id],
                "liberalAreaRequirements": areas_by_set[liberal.id],
                "consistencyWarnings": warnings_by_profile[profile.id],
                "requiresManualReview": profile.requires_manual_review,
                "sourceRefs": source_refs_by_profile[profile.id],
            }
        )
    return result


async def _assessment_rules(
    session: AsyncSession,
    canonical_keys: set[str],
) -> list[dict[str, Any]]:
    profiles = list(
        await session.scalars(
            select(GraduationAssessmentProfile)
            .where(GraduationAssessmentProfile.academic_unit_key.in_(canonical_keys))
            .order_by(GraduationAssessmentProfile.source_rule_id.asc())
        )
    )
    if not profiles:
        return []
    profile_ids = [profile.id for profile in profiles]
    source_refs_by_profile: dict[str, list[str]] = defaultdict(list)
    for source_ref in await session.scalars(
        select(GraduationAssessmentSourceReference)
        .where(GraduationAssessmentSourceReference.profile_id.in_(profile_ids))
        .order_by(
            GraduationAssessmentSourceReference.profile_id.asc(),
            GraduationAssessmentSourceReference.position.asc(),
        )
    ):
        source_refs_by_profile[source_ref.profile_id].append(source_ref.source_ref)
    categories_by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for category in await session.scalars(
        select(GraduationAssessmentCategory)
        .where(GraduationAssessmentCategory.profile_id.in_(profile_ids))
        .order_by(
            GraduationAssessmentCategory.profile_id.asc(),
            GraduationAssessmentCategory.category_code.asc(),
        )
    ):
        categories_by_profile[category.profile_id].append(
            {
                "code": category.category_code,
                "name": category.category_name,
                "primaryPolicy": _policy(
                    category.primary_none,
                    category.primary_one,
                    category.primary_two,
                ),
                "doubleMajorPolicy": {
                    "none": category.double_major_none,
                    "one": category.double_major_one,
                },
                "requirementDetail": category.requirement_detail,
                "referenceNote": category.reference_note,
                "sourceNote": category.source_note,
            }
        )
    credential_fields = (
        "international_or_national_certification",
        "private_or_other_certification",
        "foreign_language",
        "awards",
        "employment_or_experience",
        "double_major_requirement",
        "reference_note",
        "source_note",
    )
    credentials_by_profile: dict[str, list[dict[str, str]]] = defaultdict(list)
    for credential in await session.scalars(
        select(GraduationAssessmentCredential)
        .where(GraduationAssessmentCredential.profile_id.in_(profile_ids))
        .order_by(
            GraduationAssessmentCredential.profile_id.asc(),
            GraduationAssessmentCredential.position.asc(),
        )
    ):
        credentials_by_profile[credential.profile_id].append(
            _nonempty_fields(credential, credential_fields)
        )
    return [
        {
            "id": profile.source_rule_id,
            "effectiveYear": profile.effective_year,
            "scope": {"academicUnit": profile.academic_unit},
            "kind": "DEPARTMENT_ASSESSMENT_PROFILE",
            "values": {
                "transitionMode": profile.transition_mode,
                "transitionSourceText": profile.transition_source_text,
                "sourceNote": profile.source_note,
                "categories": categories_by_profile[profile.id],
                "credentialDetails": credentials_by_profile[profile.id],
            },
            "requiresManualReview": profile.requires_manual_review,
            "sourceRefs": source_refs_by_profile[profile.id],
        }
        for profile in profiles
    ]


async def _legacy_rules(
    session: AsyncSession,
    canonical_keys: set[str],
) -> list[dict[str, Any]]:
    requirements = list(
        await session.scalars(
            select(GraduationLegacyRequirement)
            .where(GraduationLegacyRequirement.academic_unit_key.in_(canonical_keys))
            .order_by(GraduationLegacyRequirement.source_rule_id.asc())
        )
    )
    if not requirements:
        return []
    requirement_ids = [requirement.id for requirement in requirements]
    source_refs_by_requirement: dict[str, list[str]] = defaultdict(list)
    for source_ref in await session.scalars(
        select(GraduationLegacySourceReference)
        .where(GraduationLegacySourceReference.legacy_requirement_id.in_(requirement_ids))
        .order_by(
            GraduationLegacySourceReference.legacy_requirement_id.asc(),
            GraduationLegacySourceReference.position.asc(),
        )
    ):
        source_refs_by_requirement[source_ref.legacy_requirement_id].append(source_ref.source_ref)
    cohorts_by_requirement: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cohort in await session.scalars(
        select(GraduationLegacyCohort)
        .where(GraduationLegacyCohort.legacy_requirement_id.in_(requirement_ids))
        .order_by(
            GraduationLegacyCohort.legacy_requirement_id.asc(),
            GraduationLegacyCohort.position.asc(),
        )
    ):
        cohorts_by_requirement[cohort.legacy_requirement_id].append(
            {
                "start": cohort.start_year,
                "end": cohort.end_year,
                "expression": cohort.expression,
            }
        )
    text_fields = (
        "eligibility_requirement",
        "substitute_international_certification",
        "substitute_national_technical_certification",
        "substitute_national_professional_certification",
        "substitute_national_accredited_private_certification",
        "substitute_private_certification",
        "substitute_other",
        "pass_requirement",
        "double_major_pass_requirement",
        "note",
    )
    result: list[dict[str, Any]] = []
    for requirement in requirements:
        values: dict[str, Any] = _nonempty_fields(requirement, text_fields)
        for field in (
            "form_thesis",
            "form_report",
            "form_practical_or_artwork",
            "form_exam",
        ):
            if getattr(requirement, field):
                values[field] = "√"
        result.append(
            {
                "id": requirement.source_rule_id,
                "effectiveYear": requirement.effective_year,
                "scope": {"academicUnit": requirement.academic_unit},
                "kind": "LEGACY_DEPARTMENT_ASSESSMENT",
                "values": {
                    "requirements": values,
                    "cohortMentions": cohorts_by_requirement[requirement.id],
                },
                "requiresManualReview": requirement.requires_manual_review,
                "sourceRefs": source_refs_by_requirement[requirement.id],
            }
        )
    return result


async def load_graduation_rules(
    session_factory: async_sessionmaker[AsyncSession],
    scope: GraduationRuleScope,
) -> tuple[dict[str, Any], ...]:
    async with session_factory() as session:
        canonical_keys = await _canonical_keys(session, scope)
        credit = await _credit_rules(session, scope, canonical_keys)
        assessments = await _assessment_rules(session, canonical_keys)
        legacy = await _legacy_rules(session, canonical_keys)
    return tuple([*credit, *assessments, *legacy])
