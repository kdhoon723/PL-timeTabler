from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from timetabler.catalog.models import (
    CatalogPage,
    CatalogSnapshot,
    CatalogStats,
    Section,
    Semester,
    Session,
)
from timetabler.catalog.parser import parse_lecture_time, time_to_minute
from timetabler.types import normalize_search_text


class DatasetIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class _RoomSession:
    session: Session


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_dataset_version(course_checksum: str, classroom_checksum: str) -> str:
    """Version every source that can change browser or optimizer behavior."""

    return f"{course_checksum[:12]}-{classroom_checksum[:12]}"


class CatalogRepository:
    def __init__(self, data_root: Path, *, validate_checksums: bool = True) -> None:
        self._data_root = data_root
        self._validate_checksums = validate_checksums
        self._snapshot: CatalogSnapshot | None = None

    @property
    def snapshot(self) -> CatalogSnapshot:
        if self._snapshot is None:
            self._snapshot = self._load()
        return self._snapshot

    def reload(self) -> CatalogSnapshot:
        self._snapshot = self._load()
        return self._snapshot

    def semesters(self) -> tuple[Semester, ...]:
        snapshot = self.snapshot
        return (
            Semester(
                id=snapshot.semester,
                prepared_at=snapshot.prepared_at,
                dataset_version=snapshot.dataset_version,
                section_count=len(snapshot.sections),
            ),
        )

    def query(
        self,
        semester: str,
        *,
        q: str | None = None,
        category: str | None = None,
        course_code: str | None = None,
        professor: str | None = None,
        offset: int = 0,
        limit: int = 2000,
    ) -> CatalogPage:
        snapshot = self.snapshot
        if semester != snapshot.semester:
            raise KeyError(semester)

        sections: Iterable[Section] = snapshot.sections
        if q:
            needle = normalize_search_text(q)
            sections = (
                item
                for item in sections
                if needle
                in normalize_search_text(
                    f"{item.course_code} {item.section_code} {item.name} "
                    f"{item.professor or ''} {item.category}"
                )
            )
        if category:
            sections = (item for item in sections if item.category == category)
        if course_code:
            sections = (item for item in sections if item.course_code == course_code)
        if professor:
            professor_needle = normalize_search_text(professor)
            sections = (
                item
                for item in sections
                if professor_needle in normalize_search_text(item.professor or "")
            )

        matched = tuple(sections)
        return CatalogPage(
            semester=snapshot.semester,
            prepared_at=snapshot.prepared_at,
            dataset_version=snapshot.dataset_version,
            total=len(matched),
            offset=offset,
            limit=limit,
            sections=matched[offset : offset + limit],
        )

    def by_id(self, semester: str) -> dict[str, Section]:
        if semester != self.snapshot.semester:
            raise KeyError(semester)
        return {section.id: section for section in self.snapshot.sections}

    def _load(self) -> CatalogSnapshot:
        manifest_path = self._data_root / "manifest.json"
        manifest = self._read_json(manifest_path)
        semester = str(manifest["semester"])
        course_path = self._data_root / "courses" / f"courses-{semester}.json"
        classroom_path = self._data_root / "classrooms" / f"classroom-sessions-{semester}.json"
        dataset_entries = {Path(str(entry["path"])).name: entry for entry in manifest["datasets"]}

        if self._validate_checksums:
            for entry in manifest["datasets"]:
                relative_path = Path(str(entry["path"]))
                if relative_path.parts and relative_path.parts[0] == "data":
                    relative_path = Path(*relative_path.parts[1:])
                self._validate_checksum(self._data_root / relative_path, entry)

        raw_courses = self._read_json(course_path)
        raw_classrooms = self._read_json(classroom_path)
        if not isinstance(raw_courses, list) or not isinstance(raw_classrooms, dict):
            raise DatasetIntegrityError("catalog fixtures have unexpected root types")

        room_sessions: dict[tuple[str, str], list[_RoomSession]] = defaultdict(list)
        rooms = raw_classrooms.get("rooms")
        if not isinstance(rooms, list):
            raise DatasetIntegrityError("classroom fixture is missing rooms")
        classroom_session_count = 0
        for room in rooms:
            for raw_session in room.get("sessions", []):
                classroom_session_count += 1
                key = (str(raw_session["curiNo"]), str(raw_session["clssNo"]))
                room_sessions[key].append(
                    _RoomSession(
                        Session(
                            day=raw_session["day"],
                            start_minute=time_to_minute(raw_session["start"]),
                            end_minute=time_to_minute(raw_session["end"]),
                            room_code=str(room["code"]),
                            room_name=str(room["ho"]),
                            building_code=str(room["bldg"]),
                            building_name=str(room["bldgName"]),
                        )
                    )
                )

        sections: list[Section] = []
        matched_sections = 0
        seen_keys: set[tuple[str, str]] = set()
        for raw_course in raw_courses:
            key = (str(raw_course["curiNo"]), str(raw_course["clssNo"]))
            if key in seen_keys:
                raise DatasetIntegrityError(f"duplicate section key: {key!r}")
            seen_keys.add(key)
            attached = room_sessions.get(key, [])
            raw_lecture_time = str(raw_course.get("lectTm") or "")
            catalog_sessions = parse_lecture_time(raw_lecture_time)
            warning_codes: list[str] = []
            if attached:
                matched_sections += 1
            sessions: list[Session] = []
            for catalog_session in catalog_sessions:
                matching_rooms = sorted(
                    (
                        item.session
                        for item in attached
                        if item.session.day == catalog_session.day
                        and item.session.start_minute == catalog_session.start_minute
                        and item.session.end_minute == catalog_session.end_minute
                    ),
                    key=lambda item: item.room_code or "",
                )
                room = matching_rooms[0] if matching_rooms else None
                if len(matching_rooms) > 1:
                    warning_codes.append("MULTIPLE_ROOM_MATCHES")
                sessions.append(
                    Session(
                        day=catalog_session.day,
                        start_minute=catalog_session.start_minute,
                        end_minute=catalog_session.end_minute,
                        room_code=room.room_code if room else None,
                        room_name=room.room_name if room else None,
                        building_code=room.building_code if room else None,
                        building_name=room.building_name if room else None,
                    )
                )
            catalog_intervals = {
                (item.day, item.start_minute, item.end_minute) for item in catalog_sessions
            }
            classroom_intervals = {
                (item.session.day, item.session.start_minute, item.session.end_minute)
                for item in attached
            }
            if attached and catalog_intervals != classroom_intervals:
                warning_codes.append("CLASSROOM_SCHEDULE_MISMATCH")

            sections.append(
                Section(
                    id=f"{key[0]}-{key[1]}",
                    course_code=key[0],
                    section_code=key[1],
                    name=str(raw_course["cousNm"]),
                    professor=str(raw_course["profNm"]).strip() or None,
                    category=str(raw_course["category"]),
                    credits=float(raw_course["pnt"]),
                    raw_lecture_time=raw_lecture_time,
                    sessions=tuple(sessions),
                    time_to_be_announced=not catalog_sessions,
                    room_to_be_announced=not catalog_sessions
                    or any(session.room_code is None for session in sessions),
                    warning_codes=tuple(sorted(set(warning_codes))),
                )
            )

        expected_records = int(dataset_entries[course_path.name]["records"])
        expected_rooms = int(dataset_entries[classroom_path.name]["rooms"])
        expected_sessions = int(dataset_entries[classroom_path.name]["sessions"])
        expected_matched = int(manifest["join"]["matchedSections"])
        observed = (len(sections), len(rooms), classroom_session_count, matched_sections)
        expected = (expected_records, expected_rooms, expected_sessions, expected_matched)
        if observed != expected:
            raise DatasetIntegrityError(
                f"manifest counts do not match fixtures: expected={expected}, observed={observed}"
            )

        return CatalogSnapshot(
            semester=semester,
            prepared_at=str(manifest["preparedAt"]),
            dataset_version=canonical_dataset_version(
                str(dataset_entries[course_path.name]["sha256"]),
                str(dataset_entries[classroom_path.name]["sha256"]),
            ),
            sections=tuple(sections),
            stats=CatalogStats(
                course_records=len(sections),
                room_records=len(rooms),
                classroom_sessions=classroom_session_count,
                classroom_section_keys=len(room_sessions),
                matched_sections=matched_sections,
            ),
        )

    def _validate_checksum(self, path: Path, entry: dict[str, Any]) -> None:
        actual = sha256_file(path)
        expected = str(entry["sha256"])
        if actual != expected:
            raise DatasetIntegrityError(
                f"checksum mismatch for {path}: expected={expected}, actual={actual}"
            )

    @staticmethod
    def _read_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DatasetIntegrityError(f"failed to load {path}: {exc}") from exc
