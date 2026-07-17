from __future__ import annotations

import hashlib
import json
import unicodedata

from timetabler.config import repository_root
from timetabler.requirements.normalizer import validate_bundle


def _review_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).replace("(야)", "")
    return "".join(character.casefold() for character in normalized if character.isalnum())


def test_curriculum_requirement_bundle_covers_2016_through_2026() -> None:
    root = repository_root()
    path = root / "data/requirements/normalized/curriculum-requirements-2016-2026.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    validate_bundle(payload)
    assert [item["admissionYear"] for item in payload["datasets"]] == list(range(2016, 2027))
    assert sum(item["programCount"] for item in payload["datasets"]) == 712
    assert sum(item["requiredCourseCount"] for item in payload["datasets"]) == 2944
    assert (
        sum(
            course["classification"] == "전기"
            for dataset in payload["datasets"]
            for program in dataset["programs"]
            for course in program["requiredCourses"]
        )
        == 284
    )


def test_2026_reviewed_major_required_courses_are_preserved() -> None:
    root = repository_root()
    bundle = json.loads(
        (root / "data/requirements/normalized/curriculum-requirements-2016-2026.json").read_text(
            encoding="utf-8"
        )
    )
    reviewed = json.loads(
        (root / "data/requirements/normalized/major-required-courses-2026.json").read_text(
            encoding="utf-8"
        )
    )
    current = next(item for item in bundle["datasets"] if item["admissionYear"] == 2026)
    by_alias = {
        _review_key(alias): program
        for program in current["programs"]
        for alias in program["academicUnitAliases"]
    }

    for expected_program in reviewed["programs"]:
        if expected_program["status"] != "AVAILABLE":
            continue
        actual_program = by_alias[_review_key(expected_program["academicUnit"])]
        expected_courses = {
            (course["courseCode"], course["name"]) for course in expected_program["courses"]
        }
        actual_courses = {
            (course["courseCode"], course["name"])
            for course in actual_program["requiredCourses"]
            if course["classification"] == "전필"
        }
        assert actual_courses == expected_courses


def test_requirement_bundle_source_checksums_match() -> None:
    root = repository_root()
    data_root = root / "data"
    bundle_path = data_root / "requirements/normalized/curriculum-requirements-2016-2026.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    for dataset in payload["datasets"]:
        source = dataset["source"]
        assert (
            hashlib.sha256((data_root / source["path"]).read_bytes()).hexdigest()
            == source["sha256"]
        )
    for source in payload["ruleSources"]:
        assert (
            hashlib.sha256((data_root / source["path"]).read_bytes()).hexdigest()
            == source["sha256"]
        )
