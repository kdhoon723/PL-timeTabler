from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from timetabler.catalog.repository import CatalogRepository
from timetabler.config import get_settings
from timetabler.db.models import (
    HistoricalArchiveManifest,
    HistoricalCourseOffering,
    HistoricalCourseRelation,
    HistoricalCurriculumDataset,
    HistoricalCurriculumDepartment,
    HistoricalRelationDataset,
    HistoricalTermDataset,
)
from timetabler.db.session import Database
from timetabler.types import normalize_search_text

ARCHIVE_MANIFEST_ID = "dreams-history"
RELATION_DATASET_ID = "dreams-relations"


@dataclass(frozen=True, slots=True)
class ImportReport:
    manifest_imported: bool
    term_datasets_imported: int
    term_datasets_unchanged: int
    offerings_imported: int
    curriculum_datasets_imported: int
    curriculum_datasets_unchanged: int
    curriculum_departments_imported: int
    relation_datasets_imported: int
    relation_datasets_unchanged: int
    relations_imported: int


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"expected ISO datetime, got {value!r}")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_json(payload: bytes, *, compressed: bool) -> dict[str, Any]:
    raw = gzip.decompress(payload) if compressed else payload
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("DREAMS archive root must be a JSON object")
    return value


def _metadata_only(payload: Mapping[str, Any], collection_key: str) -> dict[str, Any]:
    """Keep every root field except the separately stored record collection.

    The exact original gzip is also stored in the dataset row, while each member of
    the collection is stored verbatim in its own row. Together these are lossless.
    """

    return {key: value for key, value in payload.items() if key != collection_key}


def _uuid(kind: str, *parts: object) -> str:
    stable_key = ":".join(str(part) for part in parts)
    return str(uuid5(NAMESPACE_URL, f"pl-timetabler:dreams:{kind}:{stable_key}"))


def _string(value: object, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError("required DREAMS string is missing")
        return None
    result = str(value)
    if required and not result:
        raise ValueError("required DREAMS string is blank")
    return result


def _float(value: object) -> float | None:
    if value is None or value == "":
        return None
    return float(str(value))


def _list_of_objects(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("expected a list of DREAMS objects")
    return value


def _flatten_values(value: object) -> Iterable[str]:
    if isinstance(value, dict):
        for nested in value.values():
            yield from _flatten_values(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _flatten_values(nested)
    elif value is not None:
        yield str(value)


def _offering_row(
    dataset_id: str,
    academic_year: int,
    term_code: str,
    section: dict[str, Any],
) -> dict[str, Any]:
    course_code = _string(section.get("courseCode"), required=True)
    section_code = _string(section.get("sectionCode"), required=True)
    korean_name = _string(section.get("koreanName"), required=True)
    assert course_code is not None and section_code is not None and korean_name is not None
    category_contexts = _list_of_objects(section.get("categoryContexts"))
    department_contexts = _list_of_objects(section.get("departmentContexts"))
    searchable = [
        course_code,
        section_code,
        korean_name,
        _string(section.get("englishName")),
        _string(section.get("professorName")),
        _string(section.get("completionCategory")),
        *_flatten_values(category_contexts),
        *_flatten_values(department_contexts),
    ]
    return {
        "id": _uuid("offering", academic_year, term_code, course_code, section_code),
        "dataset_id": dataset_id,
        "academic_year": academic_year,
        "term_code": term_code,
        "course_code": course_code,
        "section_code": section_code,
        "korean_name": korean_name,
        "english_name": _string(section.get("englishName")),
        "professor_name": _string(section.get("professorName")),
        "completion_category": _string(section.get("completionCategory")),
        "credits": _float(section.get("credits")),
        "lecture_hours": _float(section.get("lectureHours")),
        "practice_hours": _float(section.get("practiceHours")),
        "raw_lecture_time": _string(section.get("rawLectureTime")),
        "raw_location": _string(section.get("rawLocation")),
        "target_grade": _string(section.get("targetGrade")),
        "listing_status": _string(section.get("listingStatus")),
        "detail_status": _string(section.get("detailStatus")),
        "category_contexts": category_contexts,
        "department_contexts": department_contexts,
        "search_text": normalize_search_text(" ".join(item for item in searchable if item)),
        "department_search_text": normalize_search_text(
            " ".join(_flatten_values(department_contexts))
        ),
        "raw_payload": section,
    }


def _curriculum_department_row(
    dataset_id: str,
    academic_year: int,
    department: dict[str, Any],
) -> dict[str, Any]:
    department_code = _string(department.get("departmentCode"), required=True)
    department_name = _string(department.get("departmentName"), required=True)
    courses = _list_of_objects(department.get("courses"))
    assert department_code is not None and department_name is not None
    return {
        "id": _uuid("curriculum-department", academic_year, department_code),
        "dataset_id": dataset_id,
        "academic_year": academic_year,
        "college_code": _string(department.get("collegeCode")),
        "college_name": _string(department.get("collegeName")),
        "department_code": department_code,
        "department_name": department_name,
        "course_count": len(courses),
        "raw_payload": department,
    }


def _relation_row(
    relation_type: str,
    index: int,
    relation: dict[str, Any],
) -> dict[str, Any]:
    replacement = relation_type == "REPLACEMENT"
    original_name = _string(relation.get("originalCourseName"), required=True)
    related_name = _string(
        relation.get("replacementCourseName" if replacement else "equivalentCourseName"),
        required=True,
    )
    assert original_name is not None and related_name is not None
    related_prefix = "replacement" if replacement else "equivalent"
    return {
        "id": _uuid("relation", relation_type, index, original_name, related_name),
        "dataset_id": RELATION_DATASET_ID,
        "relation_type": relation_type,
        "designated_year": _string(relation.get("designatedYear")),
        "designated_term": _string(relation.get("designatedTerm")),
        "original_course_name": original_name,
        "original_category": _string(relation.get("originalCategory")),
        "original_credits": _float(relation.get("originalCredits")),
        "original_college": _string(relation.get("originalCollege")),
        "original_department": _string(relation.get("originalDepartment")),
        "related_course_name": related_name,
        "related_category": _string(relation.get(f"{related_prefix}Category")),
        "related_credits": _float(relation.get(f"{related_prefix}Credits")),
        "related_department": _string(relation.get(f"{related_prefix}Department")),
        "note": _string(relation.get("note")),
        "raw_payload": relation,
    }


async def _upsert_single(
    session: AsyncSession,
    model: type[Any],
    row: dict[str, Any],
) -> None:
    existing = await session.get(model, row["id"])
    if existing is None:
        await session.execute(insert(model.__table__), [row])
        return
    await session.execute(
        update(model.__table__).where(model.__table__.c.id == row["id"]).values(**row)
    )


async def _replace_dataset_rows(
    session: AsyncSession,
    model: type[Any],
    dataset_id: str,
    rows: list[dict[str, Any]],
) -> None:
    existing_ids = set(
        await session.scalars(select(model.id).where(model.dataset_id == dataset_id))
    )
    desired_ids = {str(row["id"]) for row in rows}
    new_rows = [row for row in rows if row["id"] not in existing_ids]
    if new_rows:
        await session.execute(insert(model.__table__), new_rows)
    for row in rows:
        if row["id"] in existing_ids:
            await session.execute(
                update(model.__table__).where(model.__table__.c.id == row["id"]).values(**row)
            )
    obsolete = existing_ids - desired_ids
    if obsolete:
        await session.execute(delete(model).where(model.id.in_(obsolete)))


class DreamsArchiveImporter:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        dreams_root: Path,
    ) -> None:
        self._session_factory = session_factory
        self._root = dreams_root.resolve()

    def _dataset_bytes(self, relative_path: object, expected_checksum: object) -> bytes:
        if not isinstance(relative_path, str) or not isinstance(expected_checksum, str):
            raise ValueError("manifest dataset path/checksum is invalid")
        path = (self._root / relative_path).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError(f"manifest path escapes DREAMS root: {relative_path}")
        payload = path.read_bytes()
        actual_checksum = _sha256(payload)
        if actual_checksum != expected_checksum:
            raise ValueError(
                f"DREAMS checksum mismatch for {relative_path}: "
                f"expected {expected_checksum}, got {actual_checksum}"
            )
        return payload

    async def import_all(self) -> ImportReport:
        manifest_bytes = (self._root / "manifest.json").read_bytes()
        manifest = _load_json(manifest_bytes, compressed=False)
        datasets = manifest.get("datasets")
        if not isinstance(datasets, list) or not all(isinstance(item, dict) for item in datasets):
            raise ValueError("DREAMS manifest datasets must be an object list")

        counters = {
            "term_datasets_imported": 0,
            "term_datasets_unchanged": 0,
            "offerings_imported": 0,
            "curriculum_datasets_imported": 0,
            "curriculum_datasets_unchanged": 0,
            "curriculum_departments_imported": 0,
            "relation_datasets_imported": 0,
            "relation_datasets_unchanged": 0,
            "relations_imported": 0,
        }
        imported_at = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            existing_manifest = await session.get(HistoricalArchiveManifest, ARCHIVE_MANIFEST_ID)
            manifest_checksum = _sha256(manifest_bytes)
            manifest_imported = (
                existing_manifest is None or existing_manifest.source_checksum != manifest_checksum
            )
            await _upsert_single(
                session,
                HistoricalArchiveManifest,
                {
                    "id": ARCHIVE_MANIFEST_ID,
                    "schema_version": _string(manifest.get("schemaVersion"), required=True),
                    "generated_at": _parse_datetime(manifest.get("generatedAt")),
                    "source_checksum": manifest_checksum,
                    "raw_payload": manifest,
                    "source_archive": manifest_bytes,
                    "imported_at": imported_at,
                },
            )

            for entry in datasets:
                kind = entry.get("kind")
                archive = self._dataset_bytes(entry.get("path"), entry.get("sha256"))
                payload = _load_json(archive, compressed=True)
                if kind == "term":
                    await self._import_term(session, entry, archive, payload, imported_at, counters)
                elif kind == "curriculum":
                    await self._import_curriculum(
                        session, entry, archive, payload, imported_at, counters
                    )
                elif kind == "relations":
                    await self._import_relations(
                        session, entry, archive, payload, imported_at, counters
                    )
                else:
                    raise ValueError(f"unsupported DREAMS dataset kind: {kind!r}")

        return ImportReport(manifest_imported=manifest_imported, **counters)

    async def _import_term(
        self,
        session: AsyncSession,
        entry: dict[str, Any],
        archive: bytes,
        payload: dict[str, Any],
        imported_at: datetime,
        counters: dict[str, int],
    ) -> None:
        if payload.get("kind") != "dreams-term-catalog":
            raise ValueError("term dataset kind mismatch")
        academic_year = int(payload["academicYear"])
        term_code = str(payload["termCode"])
        dataset_id = f"{academic_year}-{term_code}"
        sections = _list_of_objects(payload.get("sections"))
        if len(sections) != int(entry.get("records", -1)):
            raise ValueError(f"term record count mismatch for {dataset_id}")
        checksum = str(entry["sha256"])
        existing = await session.get(HistoricalTermDataset, dataset_id)
        if existing is not None and existing.source_checksum == checksum:
            counters["term_datasets_unchanged"] += 1
            return
        dataset_row = {
            "id": dataset_id,
            "academic_year": academic_year,
            "term_code": term_code,
            "term_name": _string(payload.get("termName"), required=True),
            "data_status": _string(payload.get("dataStatus"), required=True),
            "schema_version": _string(payload.get("schemaVersion"), required=True),
            "collected_at": _parse_datetime(payload.get("collectedAt")),
            "source_checksum": checksum,
            "record_count": len(sections),
            "raw_payload": _metadata_only(payload, "sections"),
            "source_archive": archive,
            "imported_at": imported_at,
        }
        await _upsert_single(session, HistoricalTermDataset, dataset_row)
        rows = [
            _offering_row(dataset_id, academic_year, term_code, section) for section in sections
        ]
        await _replace_dataset_rows(session, HistoricalCourseOffering, dataset_id, rows)
        counters["term_datasets_imported"] += 1
        counters["offerings_imported"] += len(rows)

    async def _import_curriculum(
        self,
        session: AsyncSession,
        entry: dict[str, Any],
        archive: bytes,
        payload: dict[str, Any],
        imported_at: datetime,
        counters: dict[str, int],
    ) -> None:
        if payload.get("kind") != "dreams-curriculum":
            raise ValueError("curriculum dataset kind mismatch")
        academic_year = int(payload["academicYear"])
        dataset_id = f"curriculum-{academic_year}"
        departments = _list_of_objects(payload.get("departments"))
        course_count = sum(len(_list_of_objects(item.get("courses"))) for item in departments)
        if len(departments) != int(entry.get("departments", -1)):
            raise ValueError(f"curriculum department count mismatch for {academic_year}")
        if course_count != int(entry.get("records", -1)):
            raise ValueError(f"curriculum course count mismatch for {academic_year}")
        checksum = str(entry["sha256"])
        existing = await session.get(HistoricalCurriculumDataset, dataset_id)
        if existing is not None and existing.source_checksum == checksum:
            counters["curriculum_datasets_unchanged"] += 1
            return
        await _upsert_single(
            session,
            HistoricalCurriculumDataset,
            {
                "id": dataset_id,
                "academic_year": academic_year,
                "schema_version": _string(payload.get("schemaVersion"), required=True),
                "collected_at": _parse_datetime(payload.get("collectedAt")),
                "source_checksum": checksum,
                "department_count": len(departments),
                "course_record_count": course_count,
                "raw_payload": _metadata_only(payload, "departments"),
                "source_archive": archive,
                "imported_at": imported_at,
            },
        )
        rows = [
            _curriculum_department_row(dataset_id, academic_year, department)
            for department in departments
        ]
        await _replace_dataset_rows(session, HistoricalCurriculumDepartment, dataset_id, rows)
        counters["curriculum_datasets_imported"] += 1
        counters["curriculum_departments_imported"] += len(rows)

    async def _import_relations(
        self,
        session: AsyncSession,
        entry: dict[str, Any],
        archive: bytes,
        payload: dict[str, Any],
        imported_at: datetime,
        counters: dict[str, int],
    ) -> None:
        if payload.get("kind") != "dreams-course-relations":
            raise ValueError("relation dataset kind mismatch")
        replacements = _list_of_objects(payload.get("replacementCourses"))
        equivalents = _list_of_objects(payload.get("equivalentCourses"))
        if len(replacements) != int(entry.get("replacementRecords", -1)):
            raise ValueError("replacement relation count mismatch")
        if len(equivalents) != int(entry.get("equivalentRecords", -1)):
            raise ValueError("equivalent relation count mismatch")
        checksum = str(entry["sha256"])
        existing = await session.get(HistoricalRelationDataset, RELATION_DATASET_ID)
        if existing is not None and existing.source_checksum == checksum:
            counters["relation_datasets_unchanged"] += 1
            return
        await _upsert_single(
            session,
            HistoricalRelationDataset,
            {
                "id": RELATION_DATASET_ID,
                "schema_version": _string(payload.get("schemaVersion"), required=True),
                "collected_at": _parse_datetime(payload.get("collectedAt")),
                "source_checksum": checksum,
                "replacement_count": len(replacements),
                "equivalent_count": len(equivalents),
                "raw_payload": {
                    key: value
                    for key, value in payload.items()
                    if key not in {"replacementCourses", "equivalentCourses"}
                },
                "source_archive": archive,
                "imported_at": imported_at,
            },
        )
        rows = [
            *(
                _relation_row("REPLACEMENT", index, relation)
                for index, relation in enumerate(replacements)
            ),
            *(
                _relation_row("EQUIVALENT", index, relation)
                for index, relation in enumerate(equivalents)
            ),
        ]
        await _replace_dataset_rows(session, HistoricalCourseRelation, RELATION_DATASET_ID, rows)
        counters["relation_datasets_imported"] += 1
        counters["relations_imported"] += len(rows)


async def import_dreams_archive(database: Database, dreams_root: Path) -> ImportReport:
    return await DreamsArchiveImporter(database.session_factory, dreams_root).import_all()


async def _run() -> ImportReport:
    settings = get_settings()
    _ = CatalogRepository(settings.data_root, validate_checksums=True).snapshot
    database = Database(settings.database_url)
    try:
        return await import_dreams_archive(database, settings.data_root / "dreams")
    finally:
        await database.close()


def run() -> None:
    report = asyncio.run(_run())
    print(json.dumps({"status": "ok", **asdict(report)}, ensure_ascii=False))


if __name__ == "__main__":
    run()
