from timetabler.catalog.repository import CatalogRepository
from timetabler.config import Settings


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
