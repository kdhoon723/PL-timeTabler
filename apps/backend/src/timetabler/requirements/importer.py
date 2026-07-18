from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from timetabler.db.models import (
    CurriculumProgramAlias,
    CurriculumProgramRequirement,
    CurriculumRequiredCourse,
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
            graduation_payload = _object(
                json.loads(graduation_path.read_bytes()),
                label="graduation requirement bundle",
            )
            validate_graduation_bundle(graduation_payload)
            await self._import_rules(
                session,
                graduation_payload,
                {
                    "id": "graduation-requirements-2020-2026",
                    "kind": "NORMALIZED_GRADUATION_REQUIREMENTS",
                    "effectiveYear": 2026,
                    "path": str(GRADUATION_REQUIREMENT_BUNDLE),
                    "sha256": _sha256(graduation_path.read_bytes()),
                },
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
                "as_of": str(bundle["asOf"]),
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
            as_of = str(payload.get("asOf") or bundle["asOf"])
        else:
            text = source_bytes.decode("utf-8-sig")
            raw_rows = [dict(row) for row in csv.DictReader(StringIO(text))]
            rules = [
                _csv_rule_row(dataset_id, kind, effective_year, index, row)
                for index, row in enumerate(raw_rows)
            ]
            metadata = {"headers": list(raw_rows[0]) if raw_rows else []}
            as_of = str(bundle["asOf"])

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
