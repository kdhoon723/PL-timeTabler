from __future__ import annotations

import json

from timetabler.catalog.repository import CatalogRepository
from timetabler.config import get_settings


def run() -> None:
    settings = get_settings()
    snapshot = CatalogRepository(settings.data_root, validate_checksums=True).snapshot
    print(
        json.dumps(
            {
                "status": "ok",
                "semester": snapshot.semester,
                "datasetVersion": snapshot.dataset_version,
                "sections": snapshot.stats.course_records,
                "rooms": snapshot.stats.room_records,
                "classroomSessions": snapshot.stats.classroom_sessions,
                "classroomSectionKeys": snapshot.stats.classroom_section_keys,
                "matchedSections": snapshot.stats.matched_sections,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    run()
