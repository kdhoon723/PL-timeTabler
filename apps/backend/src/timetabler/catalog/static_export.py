from __future__ import annotations

import argparse
import json
from pathlib import Path

from timetabler.catalog.models import CatalogSnapshot
from timetabler.catalog.repository import CatalogRepository
from timetabler.config import get_settings, repository_root


def _format_minute(value: int) -> str:
    hours, minutes = divmod(value, 60)
    return f"{hours:02d}:{minutes:02d}"


def serialize_static_catalog(snapshot: CatalogSnapshot) -> dict[str, object]:
    """Build the browser fallback from the canonical backend snapshot.

    Keeping this conversion next to ``CatalogRepository`` prevents the packaged
    fallback from silently adopting classroom times that disagree with the
    authoritative course catalog.
    """

    sections: list[dict[str, object]] = []
    for section in snapshot.sections:
        sessions: list[dict[str, object]] = []
        for session in section.sessions:
            sessions.append(
                {
                    "day": session.day,
                    "start": _format_minute(session.start_minute),
                    "end": _format_minute(session.end_minute),
                    "room": session.room_name,
                    "building": session.building_name,
                }
            )
        sections.append(
            {
                "id": section.id,
                "courseCode": section.course_code,
                "sectionCode": section.section_code,
                "name": section.name,
                "professor": section.professor,
                "category": section.category,
                "credits": section.credits,
                "rawTime": section.raw_lecture_time or None,
                "sessions": sessions,
            }
        )

    academic_year, term = snapshot.semester.split("-", maxsplit=1)
    return {
        "schemaVersion": 1,
        "semester": snapshot.semester,
        "dataVersion": snapshot.dataset_version,
        "updatedAt": snapshot.prepared_at,
        "source": {
            "label": f"대진대학교 {academic_year}학년도 {term}학기 공개 개설과목",
            "url": "https://www.daejin.ac.kr/",
        },
        "sections": sections,
    }


def export_static_catalog(output_path: Path) -> None:
    settings = get_settings()
    snapshot = CatalogRepository(
        settings.data_root,
        validate_checksums=settings.catalog_validate_checksums,
    ).snapshot
    payload = serialize_static_catalog(snapshot)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(output_path)


def run() -> None:
    parser = argparse.ArgumentParser(
        description="Export the canonical catalog as the browser's packaged fallback."
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=repository_root() / "apps/web/public/data/catalog-2026-1.json",
    )
    arguments = parser.parse_args()
    export_static_catalog(arguments.output)


if __name__ == "__main__":
    run()
