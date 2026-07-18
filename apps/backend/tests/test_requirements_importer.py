from __future__ import annotations

import asyncio
import json

from sqlalchemy import func, select

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
    expected_rules = 421 + int(graduation_bundle["summary"]["rules"])

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
            assert first.rules_imported == expected_rules
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
                    == expected_rules
                )

                credit_profile = await session.scalar(
                    select(GraduationRequirementRule).where(
                        GraduationRequirementRule.rule_kind == "DEGREE_CREDIT_PROFILE",
                        GraduationRequirementRule.academic_unit_key == "컴퓨터공학전공",
                        GraduationRequirementRule.admission_year_start == 2026,
                        GraduationRequirementRule.program_path == "ADVANCED_MAJOR",
                    )
                )
                assert credit_profile is not None
                assert credit_profile.requires_manual_review is False
                assert credit_profile.raw_payload["values"]["primaryMajorMin"] == 72

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
            assert degree_profile["values"]["totalCreditsMin"] == 126
            assert degree_profile["values"]["primaryMajorMin"] == 72

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
