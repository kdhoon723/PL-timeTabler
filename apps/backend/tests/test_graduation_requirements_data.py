from __future__ import annotations

import hashlib
import json

from timetabler.config import repository_root
from timetabler.requirements.graduation_normalizer import validate_bundle


def _bundle() -> dict[str, object]:
    path = repository_root() / "data/requirements/normalized/graduation-requirements-2020-2026.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_graduation_requirement_bundle_has_complete_2020_through_2026_coverage() -> None:
    payload = _bundle()
    validate_bundle(payload)
    assert payload["summary"] == {
        "degreeCreditProfiles": 789,
        "degreeCreditProfilesByYear": {
            "2020": 87,
            "2021": 82,
            "2022": 85,
            "2023": 87,
            "2024": 98,
            "2025": 179,
            "2026": 171,
        },
        "departmentAssessmentProfiles": 66,
        "legacyDepartmentAssessmentRules": 35,
        "rules": 890,
    }


def test_degree_credit_profiles_preserve_quantitative_rules_and_liberal_courses() -> None:
    payload = _bundle()
    rules = payload["rules"]
    assert isinstance(rules, list)
    computer_2020 = next(
        rule for rule in rules if rule["id"] == "degree-credit-2020-advanced-major-컴퓨터공학전공"
    )
    assert computer_2020["values"]["totalCreditsMin"] == 130
    assert computer_2020["values"]["liberalMin"] == 36
    assert computer_2020["values"]["primaryMajorMin"] == 63
    assert {course["courseCode"] for course in computer_2020["requiredLiberalCourses"]} == {
        "001411",
        "927311",
        "927312",
        "927283",
        "927284",
        "927313",
        "927381",
    }

    computer_2026 = next(
        rule for rule in rules if rule["id"] == "degree-credit-2026-advanced-major-컴퓨터공학전공"
    )
    assert computer_2026["values"]["totalCreditsMin"] == 126
    assert computer_2026["values"]["liberalMin"] == 32
    assert computer_2026["values"]["primaryMajorMin"] == 72
    assert any(
        course["courseCode"] == "922601" and course["name"] == "AI시대의컴퓨팅사고"
        for course in computer_2026["requiredLiberalCourses"]
    )
    assert len(computer_2026["liberalAreaRequirements"]) == 6


def test_department_assessments_are_grouped_and_cohort_mentions_are_indexed() -> None:
    payload = _bundle()
    rules = payload["rules"]
    assert isinstance(rules, list)
    assessments = [rule for rule in rules if rule["kind"] == "DEPARTMENT_ASSESSMENT_PROFILE"]
    assert len(assessments) == 66
    assert all(
        {category["code"] for category in rule["values"]["categories"]} == {"A", "C", "E", "S"}
        for rule in assessments
    )

    child_studies = next(
        rule
        for rule in rules
        if rule["kind"] == "LEGACY_DEPARTMENT_ASSESSMENT"
        and rule["scope"]["academicUnit"] == "아동학과"
    )
    mentions = child_studies["values"]["cohortMentions"]
    assert {item["expression"] for item in mentions} >= {
        "20학번~ 23학번",
        "24학번",
        "25학번 이후",
    }


def test_graduation_requirement_source_checksums_match() -> None:
    root = repository_root() / "data"
    payload = _bundle()
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        path = root / source["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["sha256"]
