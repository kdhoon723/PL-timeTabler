from __future__ import annotations

import asyncio
import json

from sqlalchemy import delete, func, select

from timetabler.api.resource_schemas import RequirementProfile
from timetabler.api.routes.requirements import (
    _combined_rules,
    _database_rules,
    _evaluate_rules,
    _major_requirements,
)
from timetabler.config import Settings, repository_root
from timetabler.db.models import (
    CurriculumProgramAlias,
    CurriculumProgramRequirement,
    CurriculumRequiredCourse,
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
    GraduationRequirementRule,
    RequirementDataset,
)
from timetabler.db.session import Database
from timetabler.requirements.importer import import_requirement_data


def test_requirement_import_is_complete_and_idempotent(settings: Settings) -> None:
    data_root = repository_root() / "data"
    bundle = json.loads(
        (data_root / "requirements/normalized/curriculum-requirements-2016-2026.json").read_text(
            encoding="utf-8"
        )
    )
    expected_programs = sum(item["programCount"] for item in bundle["datasets"])
    expected_courses = sum(item["requiredCourseCount"] for item in bundle["datasets"])
    expected_aliases = sum(
        len(program["academicUnitAliases"])
        for dataset in bundle["datasets"]
        for program in dataset["programs"]
    )
    graduation_bundle = json.loads(
        (data_root / "requirements/normalized/graduation-requirements-2020-2026.json").read_text(
            encoding="utf-8"
        )
    )
    expected_source_rules = 421
    expected_imported_rules = expected_source_rules + int(graduation_bundle["summary"]["rules"])
    expected_degree_profile = next(
        rule
        for rule in graduation_bundle["rules"]
        if rule["kind"] == "DEGREE_CREDIT_PROFILE"
        and rule["scope"]["academicUnit"] == "컴퓨터공학전공"
        and rule["admissionYears"]["start"] == 2026
        and rule["scope"]["programPath"] == "ADVANCED_MAJOR"
    )
    expected_night_program_profile = next(
        rule
        for rule in graduation_bundle["rules"]
        if rule["kind"] == "DEGREE_CREDIT_PROFILE"
        and rule["scope"]["academicUnit"] == "공공인재법학과"
        and rule["admissionYears"]["start"] == 2020
        and rule["scope"]["programPath"] == "ADVANCED_MAJOR"
    )
    expected_legacy_profile = next(
        rule
        for rule in graduation_bundle["rules"]
        if rule["kind"] == "LEGACY_DEPARTMENT_ASSESSMENT"
        and rule["scope"]["academicUnit"] == "아동학과"
    )

    async def prepare() -> None:
        database = Database(settings.database_url)
        try:
            await database.create_schema()
            first = await import_requirement_data(database, data_root)
            second = await import_requirement_data(database, data_root)
            assert first.datasets_imported == 17
            assert first.programs_imported == expected_programs
            assert first.aliases_imported == expected_aliases
            assert first.required_courses_imported == expected_courses
            assert first.rules_imported == expected_imported_rules
            assert second.datasets_unchanged == 17
            assert second.datasets_imported == 0

            async with database.session_factory() as session:
                assert (
                    await session.scalar(select(func.count()).select_from(RequirementDataset)) == 17
                )
                assert (
                    await session.scalar(
                        select(func.count()).select_from(CurriculumProgramRequirement)
                    )
                    == expected_programs
                )
                assert (
                    await session.scalar(select(func.count()).select_from(CurriculumProgramAlias))
                    == expected_aliases
                )
                assert (
                    await session.scalar(select(func.count()).select_from(CurriculumRequiredCourse))
                    == expected_courses
                )
                assert (
                    await session.scalar(
                        select(func.count()).select_from(GraduationRequirementRule)
                    )
                    == expected_source_rules
                )

                credit_profile = await session.scalar(
                    select(GraduationCreditProfile).where(
                        GraduationCreditProfile.academic_unit_key == "컴퓨터공학전공",
                        GraduationCreditProfile.admission_year == 2026,
                        GraduationCreditProfile.program_path == "ADVANCED_MAJOR",
                    )
                )
                assert credit_profile is not None
                assert credit_profile.requires_manual_review is False
                assert credit_profile.total_credits_min == 126
                assert credit_profile.primary_major_min == 72

                expected_typed_counts = {
                    GraduationLiberalRequirementSet: 15,
                    GraduationLiberalRequiredCourse: 58,
                    GraduationLiberalCourseAlias: 72,
                    GraduationLiberalCourseTerm: 103,
                    GraduationLiberalAreaRequirement: 43,
                    GraduationCreditProfile: 789,
                    GraduationCreditProfileAcademicUnitAlias: 793,
                    GraduationCreditProfileSourceReference: 789,
                    GraduationCreditProfileWarning: 7,
                    GraduationAssessmentProfile: 66,
                    GraduationAssessmentSourceReference: 198,
                    GraduationAssessmentCategory: 264,
                    GraduationAssessmentCredential: 42,
                    GraduationLegacyRequirement: 35,
                    GraduationLegacySourceReference: 35,
                    GraduationLegacyCohort: 6,
                }
                for model, expected_count in expected_typed_counts.items():
                    assert (
                        await session.scalar(select(func.count()).select_from(model))
                        == expected_count
                    )

                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(GraduationRequirementRule)
                        .where(
                            GraduationRequirementRule.dataset_id
                            == "graduation-requirements-2020-2026"
                        )
                    )
                    == 0
                )

                program_id = await session.scalar(
                    select(CurriculumProgramAlias.program_id).where(
                        CurriculumProgramAlias.admission_year == 2017,
                        CurriculumProgramAlias.alias_key == "대순종학과",
                    )
                )
                assert program_id is not None
                course = (
                    await session.scalars(
                        select(CurriculumRequiredCourse).where(
                            CurriculumRequiredCourse.program_id == program_id,
                            CurriculumRequiredCourse.course_code == "041035",
                        )
                    )
                ).one()
                assert course.classification == "전필"
                assert course.course_name == "대순종학원론"

                common_alias = await session.scalar(
                    select(CurriculumProgramAlias).where(
                        CurriculumProgramAlias.admission_year == 2026,
                        CurriculumProgramAlias.alias_key == "미술만화게임학부공통",
                    )
                )
                assert common_alias is not None

            async with database.session_factory() as session:
                await session.execute(
                    delete(GraduationAssessmentSourceReference).where(
                        GraduationAssessmentSourceReference.profile_id
                        == select(GraduationAssessmentSourceReference.profile_id)
                        .limit(1)
                        .scalar_subquery()
                    )
                )
                await session.commit()

            repaired = await import_requirement_data(database, data_root)
            stable = await import_requirement_data(database, data_root)
            assert repaired.datasets_imported == 1
            assert repaired.rules_imported == 890
            assert stable.datasets_unchanged == 17
            async with database.session_factory() as session:
                assert (
                    await session.scalar(
                        select(func.count()).select_from(GraduationAssessmentSourceReference)
                    )
                    == 198
                )

            required_names, manual_reasons = await _major_requirements(
                database,
                settings,
                RequirementProfile(
                    admission_year=2017,
                    department_id="대순종학과",
                    student_type="DOMESTIC",
                    program_path="ADVANCED_MAJOR",
                ),
            )
            assert manual_reasons == ()
            assert "대순종학원론" in required_names

            profile = RequirementProfile(
                admission_year=2026,
                department_id="컴퓨터공학전공",
                student_type="DOMESTIC",
                program_path="ADVANCED_MAJOR",
            )
            database_rules = await _database_rules(database, profile)
            degree_profile = next(
                rule for rule in database_rules if rule["kind"] == "DEGREE_CREDIT_PROFILE"
            )
            assert degree_profile == expected_degree_profile

            night_program_rules = await _database_rules(
                database,
                RequirementProfile(
                    admission_year=2020,
                    department_id="공공인재법학과",
                    student_type="DOMESTIC",
                    program_path="ADVANCED_MAJOR",
                ),
            )
            night_program_profile = next(
                rule for rule in night_program_rules if rule["kind"] == "DEGREE_CREDIT_PROFILE"
            )
            assert night_program_profile == expected_night_program_profile

            child_studies_rules = await _database_rules(
                database,
                RequirementProfile(
                    admission_year=2026,
                    department_id="아동학과",
                    student_type="DOMESTIC",
                    program_path="ADVANCED_MAJOR",
                ),
            )
            legacy_profile = next(
                rule
                for rule in child_studies_rules
                if rule["kind"] == "LEGACY_DEPARTMENT_ASSESSMENT"
            )
            assert legacy_profile == expected_legacy_profile

            evaluation = _evaluate_rules(
                _combined_rules((), database_rules),
                [],
                (),
            )
            total_credits = next(
                status for status in evaluation.credit_status if status.kind == "TOTAL_CREDITS"
            )
            assert total_credits.required == 126
            assert total_credits.current == 0
            liberal_courses = next(
                status
                for status in evaluation.required_course_status
                if status.kind == "LIBERAL_REQUIRED_COURSES"
            )
            assert liberal_courses.required == 6

            foreign_rules = await _database_rules(
                database,
                profile.model_copy(update={"student_type": "INTERNATIONAL"}),
            )
            assert not any(rule["kind"] == "DEGREE_CREDIT_PROFILE" for rule in foreign_rules)
        finally:
            await database.close()

    asyncio.run(prepare())
