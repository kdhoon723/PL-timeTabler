from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from timetabler.requirements.graduation_normalizer import (
    validate_bundle as validate_graduation_bundle,
)
from timetabler.requirements.normalizer import academic_unit_key, validate_bundle

REQUIREMENT_BUNDLE = Path("requirements/normalized/curriculum-requirements-2016-2026.json")
GRADUATION_REQUIREMENT_BUNDLE = Path(
    "requirements/normalized/graduation-requirements-2020-2026.json"
)
RELATIONAL_GRADUATION_SCHEMA_VERSION = 5


@dataclass(frozen=True, slots=True)
class RequirementImportReport:
    datasets_imported: int
    datasets_unchanged: int
    programs_imported: int
    aliases_imported: int
    required_courses_imported: int
    rules_imported: int


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalized_checksum(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return _sha256(payload)


def _relational_graduation_checksum(payload: bytes) -> str:
    version = f"relational-schema:{RELATIONAL_GRADUATION_SCHEMA_VERSION}".encode()
    return _sha256(payload + b"\n" + version)


def _as_of(value: object) -> date | None:
    return date.fromisoformat(str(value)) if value else None


def _uuid(kind: str, *parts: object) -> str:
    stable_key = ":".join(str(part) for part in parts)
    return str(uuid5(NAMESPACE_URL, f"pl-timetabler:requirements:{kind}:{stable_key}"))


def _object(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _objects(value: object, *, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be an object list")
    return value


def _source_refs(rule: dict[str, Any], *, label: str) -> list[str]:
    value = rule.get("sourceRefs")
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} sourceRefs must be a non-empty string list")
    return value


def _expected_graduation_counts(
    rules: list[dict[str, Any]],
) -> tuple[tuple[type[Any], int], ...]:
    credit_rules = [rule for rule in rules if rule["kind"] == "DEGREE_CREDIT_PROFILE"]
    assessment_rules = [rule for rule in rules if rule["kind"] == "DEPARTMENT_ASSESSMENT_PROFILE"]
    legacy_rules = [rule for rule in rules if rule["kind"] == "LEGACY_DEPARTMENT_ASSESSMENT"]
    liberal_sets: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {}
    for rule in credit_rules:
        values = _object(rule["values"], label=f"{rule['id']} values")
        scope = _object(rule["scope"], label=f"{rule['id']} scope")
        years = _object(rule["admissionYears"], label=f"{rule['id']} years")
        courses = _objects(
            rule.get("requiredLiberalCourses", []),
            label=f"{rule['id']} liberal courses",
        )
        areas = _objects(
            rule.get("liberalAreaRequirements", []),
            label=f"{rule['id']} liberal areas",
        )
        signature = _normalized_checksum(
            {
                "admissionYear": int(years["start"]),
                "studentType": str(scope["studentType"]),
                "requiredCreditsMin": int(values["liberalRequiredMin"]),
                "electiveCreditsMin": int(values["liberalElectiveMin"]),
                "totalCreditsMin": int(values["liberalMin"]),
                "totalCreditsMax": (
                    int(values["liberalMax"]) if values.get("liberalMax") is not None else None
                ),
                "courses": courses,
                "areas": areas,
            }
        )
        liberal_sets.setdefault(signature, (courses, areas))

    liberal_courses = [course for courses, _ in liberal_sets.values() for course in courses]
    return (
        (GraduationLiberalRequirementSet, len(liberal_sets)),
        (GraduationLiberalRequiredCourse, len(liberal_courses)),
        (
            GraduationLiberalCourseAlias,
            sum(len(course.get("aliases", [])) for course in liberal_courses),
        ),
        (
            GraduationLiberalCourseTerm,
            sum(len(course.get("semesters", [])) for course in liberal_courses),
        ),
        (
            GraduationLiberalAreaRequirement,
            sum(len(areas) for _, areas in liberal_sets.values()),
        ),
        (GraduationCreditProfile, len(credit_rules)),
        (
            GraduationCreditProfileAcademicUnitAlias,
            sum(len(rule.get("academicUnitAliases", [])) for rule in credit_rules),
        ),
        (
            GraduationCreditProfileSourceReference,
            sum(len(_source_refs(rule, label=str(rule["id"]))) for rule in credit_rules),
        ),
        (
            GraduationCreditProfileWarning,
            sum(len(rule.get("consistencyWarnings", [])) for rule in credit_rules),
        ),
        (GraduationAssessmentProfile, len(assessment_rules)),
        (
            GraduationAssessmentSourceReference,
            sum(len(_source_refs(rule, label=str(rule["id"]))) for rule in assessment_rules),
        ),
        (
            GraduationAssessmentCategory,
            sum(
                len(_object(rule["values"], label="assessment values")["categories"])
                for rule in assessment_rules
            ),
        ),
        (
            GraduationAssessmentCredential,
            sum(
                len(_object(rule["values"], label="assessment values")["credentialDetails"])
                for rule in assessment_rules
            ),
        ),
        (GraduationLegacyRequirement, len(legacy_rules)),
        (
            GraduationLegacySourceReference,
            sum(len(_source_refs(rule, label=str(rule["id"]))) for rule in legacy_rules),
        ),
        (
            GraduationLegacyCohort,
            sum(
                len(_object(rule["values"], label="legacy values")["cohortMentions"])
                for rule in legacy_rules
            ),
        ),
    )


def _safe_path(root: Path, relative_path: object) -> Path:
    if not isinstance(relative_path, str):
        raise ValueError("requirement source path must be a string")
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"requirement source path escapes data root: {relative_path}")
    return path


async def _upsert_dataset(session: AsyncSession, row: dict[str, Any]) -> None:
    existing = await session.get(RequirementDataset, row["id"])
    if existing is None:
        await session.execute(insert(RequirementDataset), [row])
        return
    await session.execute(
        update(RequirementDataset).where(RequirementDataset.id == row["id"]).values(**row)
    )


async def _delete_curriculum_children(session: AsyncSession, dataset_id: str) -> None:
    program_ids = list(
        await session.scalars(
            select(CurriculumProgramRequirement.id).where(
                CurriculumProgramRequirement.dataset_id == dataset_id
            )
        )
    )
    if program_ids:
        await session.execute(
            delete(CurriculumProgramAlias).where(CurriculumProgramAlias.program_id.in_(program_ids))
        )
        await session.execute(
            delete(CurriculumRequiredCourse).where(
                CurriculumRequiredCourse.program_id.in_(program_ids)
            )
        )
    await session.execute(
        delete(CurriculumProgramRequirement).where(
            CurriculumProgramRequirement.dataset_id == dataset_id
        )
    )


async def _delete_normalized_graduation_children(
    session: AsyncSession,
    dataset_id: str,
) -> None:
    profile_ids = list(
        await session.scalars(
            select(GraduationCreditProfile.id).where(
                GraduationCreditProfile.dataset_id == dataset_id
            )
        )
    )
    assessment_ids = list(
        await session.scalars(
            select(GraduationAssessmentProfile.id).where(
                GraduationAssessmentProfile.dataset_id == dataset_id
            )
        )
    )
    legacy_ids = list(
        await session.scalars(
            select(GraduationLegacyRequirement.id).where(
                GraduationLegacyRequirement.dataset_id == dataset_id
            )
        )
    )
    set_ids = list(
        await session.scalars(
            select(GraduationLiberalRequirementSet.id).where(
                GraduationLiberalRequirementSet.dataset_id == dataset_id
            )
        )
    )
    if profile_ids:
        await session.execute(
            delete(GraduationCreditProfileAcademicUnitAlias).where(
                GraduationCreditProfileAcademicUnitAlias.profile_id.in_(profile_ids)
            )
        )
        await session.execute(
            delete(GraduationCreditProfileSourceReference).where(
                GraduationCreditProfileSourceReference.profile_id.in_(profile_ids)
            )
        )
        await session.execute(
            delete(GraduationCreditProfileWarning).where(
                GraduationCreditProfileWarning.profile_id.in_(profile_ids)
            )
        )
        await session.execute(
            delete(GraduationCreditProfile).where(GraduationCreditProfile.id.in_(profile_ids))
        )
    if assessment_ids:
        await session.execute(
            delete(GraduationAssessmentSourceReference).where(
                GraduationAssessmentSourceReference.profile_id.in_(assessment_ids)
            )
        )
        await session.execute(
            delete(GraduationAssessmentCategory).where(
                GraduationAssessmentCategory.profile_id.in_(assessment_ids)
            )
        )
        await session.execute(
            delete(GraduationAssessmentCredential).where(
                GraduationAssessmentCredential.profile_id.in_(assessment_ids)
            )
        )
        await session.execute(
            delete(GraduationAssessmentProfile).where(
                GraduationAssessmentProfile.id.in_(assessment_ids)
            )
        )
    if legacy_ids:
        await session.execute(
            delete(GraduationLegacySourceReference).where(
                GraduationLegacySourceReference.legacy_requirement_id.in_(legacy_ids)
            )
        )
        await session.execute(
            delete(GraduationLegacyCohort).where(
                GraduationLegacyCohort.legacy_requirement_id.in_(legacy_ids)
            )
        )
        await session.execute(
            delete(GraduationLegacyRequirement).where(
                GraduationLegacyRequirement.id.in_(legacy_ids)
            )
        )
    if set_ids:
        course_ids = list(
            await session.scalars(
                select(GraduationLiberalRequiredCourse.id).where(
                    GraduationLiberalRequiredCourse.requirement_set_id.in_(set_ids)
                )
            )
        )
        if course_ids:
            await session.execute(
                delete(GraduationLiberalCourseAlias).where(
                    GraduationLiberalCourseAlias.course_id.in_(course_ids)
                )
            )
            await session.execute(
                delete(GraduationLiberalCourseTerm).where(
                    GraduationLiberalCourseTerm.course_id.in_(course_ids)
                )
            )
            await session.execute(
                delete(GraduationLiberalRequiredCourse).where(
                    GraduationLiberalRequiredCourse.id.in_(course_ids)
                )
            )
        await session.execute(
            delete(GraduationLiberalAreaRequirement).where(
                GraduationLiberalAreaRequirement.requirement_set_id.in_(set_ids)
            )
        )
        await session.execute(
            delete(GraduationLiberalRequirementSet).where(
                GraduationLiberalRequirementSet.id.in_(set_ids)
            )
        )
    await session.execute(
        delete(GraduationRequirementRule).where(GraduationRequirementRule.dataset_id == dataset_id)
    )


def _description(kind: str, row: dict[str, Any]) -> str | None:
    preferred_fields = {
        "GRADUATION_TRANSITION": ("transition_2026", "source_note"),
        "GRADUATION_STANDARDIZED": ("requirement_detail", "category_name"),
        "GRADUATION_LEGACY": (
            "pass_requirement",
            "eligibility_requirement",
            "double_major_pass_requirement",
        ),
    }
    if kind == "GRADUATION_CREDENTIALS":
        ignored = {"source_row_number", "source_number", "academic_unit"}
        values = [
            f"{key}: {value}"
            for key, value in row.items()
            if key not in ignored and isinstance(value, str) and value.strip()
        ]
        return " | ".join(values) or None
    for field in preferred_fields.get(kind, ()):
        value = row.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _common_rule_row(dataset_id: str, index: int, rule: dict[str, Any]) -> dict[str, Any]:
    years = _object(rule.get("admissionYears", {}), label="common rule admissionYears")
    scope = _object(rule.get("scope", {}), label="common rule scope")
    academic_unit = scope.get("academicUnit")
    return {
        "id": _uuid("rule", dataset_id, rule.get("id", index)),
        "dataset_id": dataset_id,
        "rule_kind": str(rule["kind"]),
        "category_code": None,
        "academic_unit": str(academic_unit) if academic_unit else None,
        "academic_unit_key": academic_unit_key(str(academic_unit)) if academic_unit else None,
        "admission_year_start": int(years["start"]) if years.get("start") else None,
        "admission_year_end": int(years["end"]) if years.get("end") else None,
        "effective_year": (int(rule["effectiveYear"]) if rule.get("effectiveYear") else None),
        "student_type": str(scope["studentType"]) if scope.get("studentType") else None,
        "program_path": str(scope["programPath"]) if scope.get("programPath") else None,
        "description": str(rule.get("id")) if rule.get("id") else None,
        "requires_manual_review": bool(rule.get("requiresManualReview", False)),
        "raw_payload": rule,
    }


def _csv_rule_row(
    dataset_id: str,
    kind: str,
    effective_year: int | None,
    index: int,
    row: dict[str, Any],
) -> dict[str, Any]:
    academic_unit = row.get("academic_unit") or None
    return {
        "id": _uuid("rule", dataset_id, index),
        "dataset_id": dataset_id,
        "rule_kind": kind,
        "category_code": row.get("category_code") or None,
        "academic_unit": academic_unit,
        "academic_unit_key": academic_unit_key(academic_unit) if academic_unit else None,
        "admission_year_start": None,
        "admission_year_end": None,
        "effective_year": effective_year,
        "student_type": None,
        "program_path": None,
        "description": _description(kind, row),
        "requires_manual_review": True,
        "raw_payload": row,
    }


class RequirementDataImporter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        data_root: Path,
    ) -> None:
        self._session_factory = session_factory
        self._root = data_root.resolve()

    async def import_all(self) -> RequirementImportReport:
        bundle_path = self._root / REQUIREMENT_BUNDLE
        bundle_bytes = bundle_path.read_bytes()
        bundle = _object(json.loads(bundle_bytes), label="requirement bundle")
        validate_bundle(bundle)
        counters = {
            "datasets_imported": 0,
            "datasets_unchanged": 0,
            "programs_imported": 0,
            "aliases_imported": 0,
            "required_courses_imported": 0,
            "rules_imported": 0,
        }
        imported_at = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            for dataset in _objects(bundle.get("datasets"), label="curriculum datasets"):
                await self._import_curriculum(
                    session,
                    bundle,
                    dataset,
                    imported_at,
                    counters,
                )
            for source in _objects(bundle.get("ruleSources"), label="rule sources"):
                await self._import_rules(session, bundle, source, imported_at, counters)
            graduation_path = self._root / GRADUATION_REQUIREMENT_BUNDLE
            graduation_source_bytes = graduation_path.read_bytes()
            graduation_payload = _object(
                json.loads(graduation_source_bytes),
                label="graduation requirement bundle",
            )
            validate_graduation_bundle(graduation_payload)
            await self._import_normalized_graduation(
                session,
                graduation_payload,
                graduation_source_bytes,
                imported_at,
                counters,
            )
        return RequirementImportReport(**counters)

    async def _import_curriculum(
        self,
        session: AsyncSession,
        bundle: dict[str, Any],
        dataset: dict[str, Any],
        imported_at: datetime,
        counters: dict[str, int],
    ) -> None:
        dataset_id = str(dataset["id"])
        source = _object(dataset.get("source"), label=f"{dataset_id} source")
        source_path = _safe_path(self._root, source.get("path"))
        source_checksum = _sha256(source_path.read_bytes())
        if source_checksum != source.get("sha256"):
            raise ValueError(f"requirement source checksum mismatch: {source_path}")
        normalized_checksum = _normalized_checksum(dataset)
        existing = await session.get(RequirementDataset, dataset_id)
        if existing is not None and existing.normalized_checksum == normalized_checksum:
            counters["datasets_unchanged"] += 1
            return

        programs = _objects(dataset.get("programs"), label=f"{dataset_id} programs")
        await _upsert_dataset(
            session,
            {
                "id": dataset_id,
                "kind": str(dataset["kind"]),
                "schema_version": str(bundle["schemaVersion"]),
                "admission_year": int(dataset["admissionYear"]),
                "effective_year": None,
                "as_of": _as_of(bundle["asOf"]),
                "source_path": str(source["path"]),
                "source_checksum": source_checksum,
                "normalized_checksum": normalized_checksum,
                "record_count": len(programs),
                "raw_payload": {key: value for key, value in dataset.items() if key != "programs"},
                "imported_at": imported_at,
            },
        )
        await _delete_curriculum_children(session, dataset_id)
        program_rows: list[dict[str, Any]] = []
        alias_rows: list[dict[str, Any]] = []
        course_rows: list[dict[str, Any]] = []
        admission_year = int(dataset["admissionYear"])
        for program in programs:
            unit_key = str(program["academicUnitKey"])
            program_id = _uuid("program", admission_year, unit_key)
            courses = _objects(
                program.get("requiredCourses"),
                label=f"{admission_year} {program['academicUnit']} required courses",
            )
            program_rows.append(
                {
                    "id": program_id,
                    "dataset_id": dataset_id,
                    "admission_year": admission_year,
                    "academic_unit": str(program["academicUnit"]),
                    "academic_unit_key": unit_key,
                    "status": str(program["status"]),
                    "source_locators": program["sourceLocators"],
                    "source_course_count": int(program["sourceCourseCount"]),
                    "required_course_count": len(courses),
                    "raw_payload": {
                        key: value for key, value in program.items() if key != "requiredCourses"
                    },
                }
            )
            aliases = program.get("academicUnitAliases", [program["academicUnit"]])
            if not isinstance(aliases, list) or not all(
                isinstance(alias, str) for alias in aliases
            ):
                raise ValueError(f"{admission_year} {program['academicUnit']} aliases are invalid")
            for alias in aliases:
                alias_rows.append(
                    {
                        "id": _uuid(
                            "program-alias", admission_year, unit_key, academic_unit_key(alias)
                        ),
                        "program_id": program_id,
                        "admission_year": admission_year,
                        "alias": alias,
                        "alias_key": academic_unit_key(alias),
                        "is_primary": alias == program["academicUnit"],
                    }
                )
            for course in courses:
                classification = str(course["classification"])
                course_code = str(course["courseCode"])
                course_rows.append(
                    {
                        "id": _uuid("required-course", program_id, classification, course_code),
                        "program_id": program_id,
                        "classification": classification,
                        "course_code": course_code,
                        "course_name": str(course["name"]),
                        "credits": (
                            float(course["credits"]) if course.get("credits") is not None else None
                        ),
                        "grade": int(course["grade"]) if course.get("grade") is not None else None,
                        "semesters": course["semesters"],
                        "source_locator": course["sourceLocator"],
                        "raw_payload": course,
                    }
                )
        if program_rows:
            await session.execute(insert(CurriculumProgramRequirement), program_rows)
        if alias_rows:
            await session.execute(insert(CurriculumProgramAlias), alias_rows)
        if course_rows:
            await session.execute(insert(CurriculumRequiredCourse), course_rows)
        counters["datasets_imported"] += 1
        counters["programs_imported"] += len(program_rows)
        counters["aliases_imported"] += len(alias_rows)
        counters["required_courses_imported"] += len(course_rows)

    async def _import_normalized_graduation(
        self,
        session: AsyncSession,
        payload: dict[str, Any],
        source_bytes: bytes,
        imported_at: datetime,
        counters: dict[str, int],
    ) -> None:
        dataset_id = "graduation-requirements-2020-2026"
        source_checksum = _sha256(source_bytes)
        normalized_checksum = _relational_graduation_checksum(source_bytes)
        rules = _objects(payload.get("rules"), label=f"{dataset_id} rules")
        expected_counts = _expected_graduation_counts(rules)
        existing = await session.get(RequirementDataset, dataset_id)
        if existing is not None and existing.normalized_checksum == normalized_checksum:
            relational_shape_complete = True
            for model, expected_count in expected_counts:
                actual_count = int(
                    await session.scalar(select(func.count()).select_from(model)) or 0
                )
                if actual_count != expected_count:
                    relational_shape_complete = False
                    break
            source_rule_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(GraduationRequirementRule)
                    .where(GraduationRequirementRule.dataset_id == dataset_id)
                )
                or 0
            )
            if relational_shape_complete and source_rule_count == 0:
                counters["datasets_unchanged"] += 1
                return

        await _upsert_dataset(
            session,
            {
                "id": dataset_id,
                "kind": "NORMALIZED_GRADUATION_REQUIREMENTS",
                "schema_version": str(RELATIONAL_GRADUATION_SCHEMA_VERSION),
                "admission_year": None,
                "effective_year": int(payload["admissionYearRange"]["end"]),
                "as_of": _as_of(payload.get("asOf")),
                "source_path": str(GRADUATION_REQUIREMENT_BUNDLE),
                "source_checksum": source_checksum,
                "normalized_checksum": normalized_checksum,
                "record_count": len(rules),
                "raw_payload": {key: value for key, value in payload.items() if key != "rules"},
                "imported_at": imported_at,
            },
        )
        await _delete_normalized_graduation_children(session, dataset_id)

        liberal_set_rows: list[dict[str, Any]] = []
        liberal_course_rows: list[dict[str, Any]] = []
        liberal_alias_rows: list[dict[str, Any]] = []
        liberal_term_rows: list[dict[str, Any]] = []
        liberal_area_rows: list[dict[str, Any]] = []
        profile_rows: list[dict[str, Any]] = []
        profile_alias_rows: list[dict[str, Any]] = []
        profile_source_ref_rows: list[dict[str, Any]] = []
        warning_rows: list[dict[str, Any]] = []
        assessment_rows: list[dict[str, Any]] = []
        assessment_source_ref_rows: list[dict[str, Any]] = []
        assessment_category_rows: list[dict[str, Any]] = []
        assessment_credential_rows: list[dict[str, Any]] = []
        legacy_rows: list[dict[str, Any]] = []
        legacy_source_ref_rows: list[dict[str, Any]] = []
        legacy_cohort_rows: list[dict[str, Any]] = []
        liberal_set_ids: dict[str, str] = {}

        for rule in rules:
            kind = str(rule["kind"])
            scope = _object(rule.get("scope", {}), label=f"{kind} scope")
            academic_unit = str(scope["academicUnit"])
            unit_key = academic_unit_key(academic_unit)
            source_rule_id = str(rule["id"])
            if kind == "DEGREE_CREDIT_PROFILE":
                years = _object(rule["admissionYears"], label=f"{source_rule_id} years")
                admission_year = int(years["start"])
                if admission_year != int(years["end"]):
                    raise ValueError(f"{source_rule_id} must target one admission year")
                values = _object(rule["values"], label=f"{source_rule_id} values")
                courses = _objects(
                    rule.get("requiredLiberalCourses", []),
                    label=f"{source_rule_id} liberal courses",
                )
                areas = _objects(
                    rule.get("liberalAreaRequirements", []),
                    label=f"{source_rule_id} liberal areas",
                )
                liberal_payload = {
                    "admissionYear": admission_year,
                    "studentType": str(scope["studentType"]),
                    "requiredCreditsMin": int(values["liberalRequiredMin"]),
                    "electiveCreditsMin": int(values["liberalElectiveMin"]),
                    "totalCreditsMin": int(values["liberalMin"]),
                    "totalCreditsMax": (
                        int(values["liberalMax"]) if values.get("liberalMax") is not None else None
                    ),
                    "courses": courses,
                    "areas": areas,
                }
                signature = _normalized_checksum(liberal_payload)
                liberal_set_id = liberal_set_ids.get(signature)
                if liberal_set_id is None:
                    liberal_set_id = _uuid("liberal-set", dataset_id, signature)
                    liberal_set_ids[signature] = liberal_set_id
                    liberal_set_rows.append(
                        {
                            "id": liberal_set_id,
                            "dataset_id": dataset_id,
                            "signature": signature,
                            "admission_year": admission_year,
                            "student_type": str(scope["studentType"]),
                            "required_credits_min": int(values["liberalRequiredMin"]),
                            "elective_credits_min": int(values["liberalElectiveMin"]),
                            "total_credits_min": int(values["liberalMin"]),
                            "total_credits_max": (
                                int(values["liberalMax"])
                                if values.get("liberalMax") is not None
                                else None
                            ),
                        }
                    )
                    for position, course in enumerate(courses):
                        course_id = _uuid("liberal-course", liberal_set_id, position)
                        locator = _object(
                            course.get("sourceLocator", {}),
                            label=f"{source_rule_id} liberal course locator",
                        )
                        liberal_course_rows.append(
                            {
                                "id": course_id,
                                "requirement_set_id": liberal_set_id,
                                "position": position,
                                "course_code": (
                                    str(course["courseCode"]) if course.get("courseCode") else None
                                ),
                                "course_name": str(course["name"]),
                                "credits": int(course["credits"]),
                                "grade": (
                                    int(course["grade"])
                                    if course.get("grade") is not None
                                    else None
                                ),
                                "source_page": int(locator["page"]),
                            }
                        )
                        for alias_position, alias in enumerate(course.get("aliases", [])):
                            alias_text = str(alias)
                            liberal_alias_rows.append(
                                {
                                    "id": _uuid(
                                        "liberal-course-alias",
                                        course_id,
                                        academic_unit_key(alias_text),
                                    ),
                                    "course_id": course_id,
                                    "position": alias_position,
                                    "alias": alias_text,
                                    "alias_key": academic_unit_key(alias_text),
                                }
                            )
                        for semester in course.get("semesters", []):
                            liberal_term_rows.append(
                                {"course_id": course_id, "semester": int(semester)}
                            )
                    for position, area in enumerate(areas):
                        liberal_area_rows.append(
                            {
                                "id": _uuid("liberal-area", liberal_set_id, position),
                                "requirement_set_id": liberal_set_id,
                                "position": position,
                                "area": str(area["area"]),
                                "min_courses": int(area.get("minCourses") or 0),
                                "min_credits": (
                                    int(area["minCredits"])
                                    if area.get("minCredits") is not None
                                    else None
                                ),
                            }
                        )

                profile_id = _uuid("credit-profile", dataset_id, source_rule_id)
                profile_rows.append(
                    {
                        "id": profile_id,
                        "dataset_id": dataset_id,
                        "source_rule_id": source_rule_id,
                        "liberal_requirement_set_id": liberal_set_id,
                        "academic_unit": academic_unit,
                        "academic_unit_key": unit_key,
                        "admission_year": admission_year,
                        "student_type": str(scope["studentType"]),
                        "program_path": str(scope["programPath"]),
                        "total_credits_min": int(values["totalCreditsMin"]),
                        "major_foundation_min": int(values["majorFoundationMin"]),
                        "major_required_min": int(values["majorRequiredMin"]),
                        "major_elective_min": int(values["majorElectiveMin"]),
                        "additional_major_min": (
                            int(values["additionalMajorMin"])
                            if values.get("additionalMajorMin") is not None
                            else None
                        ),
                        "primary_major_min": int(values["primaryMajorMin"]),
                        "secondary_program_min": (
                            int(values["secondaryProgramMin"])
                            if values.get("secondaryProgramMin") is not None
                            else None
                        ),
                        "requires_manual_review": bool(rule.get("requiresManualReview", False)),
                    }
                )
                aliases = rule.get("academicUnitAliases")
                if not isinstance(aliases, list) or not aliases:
                    raise ValueError(f"{source_rule_id} must have academic unit aliases")
                for position, alias in enumerate(aliases):
                    alias_text = str(alias)
                    profile_alias_rows.append(
                        {
                            "profile_id": profile_id,
                            "position": position,
                            "alias": alias_text,
                            "alias_key": academic_unit_key(alias_text),
                        }
                    )
                for position, source_ref in enumerate(_source_refs(rule, label=source_rule_id)):
                    profile_source_ref_rows.append(
                        {
                            "profile_id": profile_id,
                            "position": position,
                            "source_ref": source_ref,
                        }
                    )
                for position, warning in enumerate(
                    _objects(
                        rule.get("consistencyWarnings", []),
                        label=f"{source_rule_id} consistency warnings",
                    )
                ):
                    warning_rows.append(
                        {
                            "id": _uuid("credit-profile-warning", profile_id, warning["code"]),
                            "profile_id": profile_id,
                            "position": position,
                            "code": str(warning["code"]),
                            "calculated": int(warning["calculated"]),
                            "printed": int(warning["printed"]),
                        }
                    )
                continue

            effective_year = int(rule["effectiveYear"])
            values = _object(rule["values"], label=f"{source_rule_id} values")
            if kind == "DEPARTMENT_ASSESSMENT_PROFILE":
                assessment_id = _uuid("assessment-profile", dataset_id, source_rule_id)
                assessment_rows.append(
                    {
                        "id": assessment_id,
                        "dataset_id": dataset_id,
                        "source_rule_id": source_rule_id,
                        "effective_year": effective_year,
                        "academic_unit": academic_unit,
                        "academic_unit_key": unit_key,
                        "transition_mode": str(values["transitionMode"]),
                        "transition_source_text": str(values["transitionSourceText"]),
                        "source_note": (
                            str(values["sourceNote"]) if values.get("sourceNote") else None
                        ),
                        "requires_manual_review": bool(rule.get("requiresManualReview", False)),
                    }
                )
                for position, source_ref in enumerate(_source_refs(rule, label=source_rule_id)):
                    assessment_source_ref_rows.append(
                        {
                            "profile_id": assessment_id,
                            "position": position,
                            "source_ref": source_ref,
                        }
                    )
                for category in _objects(
                    values.get("categories", []),
                    label=f"{source_rule_id} assessment categories",
                ):
                    primary = _object(
                        category["primaryPolicy"],
                        label=f"{source_rule_id} primary policy",
                    )
                    double = _object(
                        category["doubleMajorPolicy"],
                        label=f"{source_rule_id} double-major policy",
                    )
                    assessment_category_rows.append(
                        {
                            "id": _uuid("assessment-category", assessment_id, category["code"]),
                            "profile_id": assessment_id,
                            "category_code": str(category["code"]),
                            "category_name": str(category["name"]),
                            "primary_none": primary.get("none"),
                            "primary_one": primary.get("one"),
                            "primary_two": primary.get("two"),
                            "double_major_none": double.get("none"),
                            "double_major_one": double.get("one"),
                            "requirement_detail": category.get("requirementDetail"),
                            "reference_note": category.get("referenceNote"),
                            "source_note": category.get("sourceNote"),
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
                for position, credential in enumerate(
                    _objects(
                        values.get("credentialDetails", []),
                        label=f"{source_rule_id} credential details",
                    )
                ):
                    assessment_credential_rows.append(
                        {
                            "id": _uuid("assessment-credential", assessment_id, position),
                            "profile_id": assessment_id,
                            "position": position,
                            **{field: credential.get(field) for field in credential_fields},
                        }
                    )
                continue

            if kind == "LEGACY_DEPARTMENT_ASSESSMENT":
                requirements = _object(
                    values.get("requirements", {}),
                    label=f"{source_rule_id} legacy requirements",
                )
                legacy_id = _uuid("legacy-requirement", dataset_id, source_rule_id)
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
                legacy_rows.append(
                    {
                        "id": legacy_id,
                        "dataset_id": dataset_id,
                        "source_rule_id": source_rule_id,
                        "effective_year": effective_year,
                        "academic_unit": academic_unit,
                        "academic_unit_key": unit_key,
                        **{field: requirements.get(field) for field in text_fields},
                        "form_thesis": bool(requirements.get("form_thesis")),
                        "form_report": bool(requirements.get("form_report")),
                        "form_practical_or_artwork": bool(
                            requirements.get("form_practical_or_artwork")
                        ),
                        "form_exam": bool(requirements.get("form_exam")),
                        "requires_manual_review": bool(rule.get("requiresManualReview", False)),
                    }
                )
                for position, source_ref in enumerate(_source_refs(rule, label=source_rule_id)):
                    legacy_source_ref_rows.append(
                        {
                            "legacy_requirement_id": legacy_id,
                            "position": position,
                            "source_ref": source_ref,
                        }
                    )
                for position, cohort in enumerate(
                    _objects(
                        values.get("cohortMentions", []),
                        label=f"{source_rule_id} cohort mentions",
                    )
                ):
                    legacy_cohort_rows.append(
                        {
                            "id": _uuid("legacy-cohort", legacy_id, cohort["expression"]),
                            "legacy_requirement_id": legacy_id,
                            "position": position,
                            "start_year": (
                                int(cohort["start"]) if cohort.get("start") is not None else None
                            ),
                            "end_year": (
                                int(cohort["end"]) if cohort.get("end") is not None else None
                            ),
                            "expression": str(cohort["expression"]),
                        }
                    )
                continue
            raise ValueError(f"unsupported normalized graduation rule kind: {kind}")

        inserts: tuple[tuple[type[Any], list[dict[str, Any]]], ...] = (
            (GraduationLiberalRequirementSet, liberal_set_rows),
            (GraduationLiberalRequiredCourse, liberal_course_rows),
            (GraduationLiberalCourseAlias, liberal_alias_rows),
            (GraduationLiberalCourseTerm, liberal_term_rows),
            (GraduationLiberalAreaRequirement, liberal_area_rows),
            (GraduationCreditProfile, profile_rows),
            (GraduationCreditProfileAcademicUnitAlias, profile_alias_rows),
            (GraduationCreditProfileSourceReference, profile_source_ref_rows),
            (GraduationCreditProfileWarning, warning_rows),
            (GraduationAssessmentProfile, assessment_rows),
            (GraduationAssessmentSourceReference, assessment_source_ref_rows),
            (GraduationAssessmentCategory, assessment_category_rows),
            (GraduationAssessmentCredential, assessment_credential_rows),
            (GraduationLegacyRequirement, legacy_rows),
            (GraduationLegacySourceReference, legacy_source_ref_rows),
            (GraduationLegacyCohort, legacy_cohort_rows),
        )
        for model, rows in inserts:
            if rows:
                await session.execute(insert(model), rows)
        typed_rule_count = len(profile_rows) + len(assessment_rows) + len(legacy_rows)
        if typed_rule_count != len(rules):
            raise ValueError(
                f"normalized graduation rule count mismatch: {typed_rule_count} != {len(rules)}"
            )
        counters["datasets_imported"] += 1
        counters["rules_imported"] += typed_rule_count

    async def _import_rules(
        self,
        session: AsyncSession,
        bundle: dict[str, Any],
        source: dict[str, Any],
        imported_at: datetime,
        counters: dict[str, int],
    ) -> None:
        dataset_id = str(source["id"])
        source_path = _safe_path(self._root, source.get("path"))
        source_bytes = source_path.read_bytes()
        checksum = _sha256(source_bytes)
        if checksum != source.get("sha256"):
            raise ValueError(f"requirement rule checksum mismatch: {source_path}")
        existing = await session.get(RequirementDataset, dataset_id)
        if existing is not None and existing.normalized_checksum == checksum:
            counters["datasets_unchanged"] += 1
            return

        kind = str(source["kind"])
        effective_year = int(source["effectiveYear"]) if source.get("effectiveYear") else None
        if source_path.suffix == ".json":
            payload = _object(json.loads(source_bytes), label=dataset_id)
            raw_rules = _objects(payload.get("rules"), label=f"{dataset_id} rules")
            rules = [
                _common_rule_row(dataset_id, index, rule) for index, rule in enumerate(raw_rules)
            ]
            metadata = {key: value for key, value in payload.items() if key != "rules"}
            as_of = _as_of(payload.get("asOf") or bundle["asOf"])
        else:
            text = source_bytes.decode("utf-8-sig")
            raw_rows = [dict(row) for row in csv.DictReader(StringIO(text))]
            rules = [
                _csv_rule_row(dataset_id, kind, effective_year, index, row)
                for index, row in enumerate(raw_rows)
            ]
            metadata = {"headers": list(raw_rows[0]) if raw_rows else []}
            as_of = _as_of(bundle["asOf"])

        await _upsert_dataset(
            session,
            {
                "id": dataset_id,
                "kind": kind,
                "schema_version": str(bundle["schemaVersion"]),
                "admission_year": None,
                "effective_year": effective_year,
                "as_of": as_of,
                "source_path": str(source["path"]),
                "source_checksum": checksum,
                "normalized_checksum": checksum,
                "record_count": len(rules),
                "raw_payload": metadata,
                "imported_at": imported_at,
            },
        )
        await session.execute(
            delete(GraduationRequirementRule).where(
                GraduationRequirementRule.dataset_id == dataset_id
            )
        )
        if rules:
            await session.execute(insert(GraduationRequirementRule), rules)
        counters["datasets_imported"] += 1
        counters["rules_imported"] += len(rules)


async def import_requirement_data(
    database: Database,
    data_root: Path,
) -> RequirementImportReport:
    return await RequirementDataImporter(database.session_factory, data_root).import_all()
