import json
import shutil
from pathlib import Path

from timetabler.catalog.repository import CatalogRepository, sha256_file
from timetabler.catalog.static_export import serialize_static_catalog
from timetabler.config import Settings, repository_root


def test_catalog_manifest_counts_and_join(settings: Settings) -> None:
    snapshot = CatalogRepository(settings.data_root).snapshot

    assert snapshot.semester == "2026-1"
    assert snapshot.stats.course_records == 1576
    assert snapshot.stats.room_records == 325
    assert snapshot.stats.classroom_sessions == 1693
    assert snapshot.stats.classroom_section_keys == 1342
    assert snapshot.stats.matched_sections == 1336
    assert len({section.id for section in snapshot.sections}) == 1576


def test_catalog_preserves_tba_and_large_credit_values(settings: Settings) -> None:
    snapshot = CatalogRepository(settings.data_root).snapshot

    assert sum(section.time_to_be_announced for section in snapshot.sections) == 13
    assert {section.credits for section in snapshot.sections} >= {1.0, 2.0, 3.0, 12.0, 15.0}


def test_catalog_search_is_whitespace_insensitive(settings: Settings) -> None:
    repository = CatalogRepository(settings.data_root)

    result = repository.query("2026-1", q="AI 시대의 컴퓨팅 사고")

    assert result.total > 0
    assert all(section.name == "AI시대의컴퓨팅사고" for section in result.sections)


def test_catalog_timing_remains_authoritative_over_room_enrichment(settings: Settings) -> None:
    snapshot = CatalogRepository(settings.data_root).snapshot
    mismatches = [
        section
        for section in snapshot.sections
        if "CLASSROOM_SCHEDULE_MISMATCH" in section.warning_codes
    ]

    assert len(mismatches) == 35
    for section in mismatches:
        assert section.raw_lecture_time
        assert section.sessions


def test_packaged_fallback_matches_every_canonical_section(settings: Settings) -> None:
    static_catalog = json.loads(
        (repository_root() / "apps/web/public/data/catalog-2026-1.json").read_text(encoding="utf-8")
    )
    snapshot = CatalogRepository(settings.data_root).snapshot

    assert static_catalog == serialize_static_catalog(snapshot)

    # This known source disagreement previously exposed classroom Tuesday in
    # the fallback while the API correctly exposed the catalog's Wednesday.
    section = next(item for item in static_catalog["sections"] if item["id"] == "927283-01")
    assert section["sessions"] == [
        {
            "day": "수",
            "start": "15:30",
            "end": "17:30",
            "room": None,
            "building": None,
        }
    ]


def test_classroom_only_change_rotates_dataset_version(settings: Settings, tmp_path: Path) -> None:
    copied_data = tmp_path / "data"
    (copied_data / "courses").mkdir(parents=True)
    (copied_data / "classrooms").mkdir()
    shutil.copy2(settings.data_root / "manifest.json", copied_data / "manifest.json")
    shutil.copy2(
        settings.data_root / "courses/courses-2026-1.json",
        copied_data / "courses/courses-2026-1.json",
    )
    shutil.copy2(
        settings.data_root / "classrooms/classroom-sessions-2026-1.json",
        copied_data / "classrooms/classroom-sessions-2026-1.json",
    )
    before = CatalogRepository(copied_data, validate_checksums=False).snapshot.dataset_version

    classroom_path = copied_data / "classrooms/classroom-sessions-2026-1.json"
    classroom = json.loads(classroom_path.read_text(encoding="utf-8"))
    classroom["versionProbe"] = "room-only-change"
    classroom_path.write_text(
        json.dumps(classroom, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    manifest_path = copied_data / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    classroom_entry = next(
        item
        for item in manifest["datasets"]
        if item["path"].endswith("classroom-sessions-2026-1.json")
    )
    classroom_entry["sha256"] = sha256_file(classroom_path)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    after = CatalogRepository(copied_data, validate_checksums=False).snapshot.dataset_version

    assert after != before
    assert after.split("-")[0] == before.split("-")[0]
