from __future__ import annotations

import json
import unicodedata

from timetabler.config import repository_root


def normalized(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKC", value).casefold() if not char.isspace()
    )


def test_major_required_snapshot_is_well_formed_and_matches_catalog() -> None:
    root = repository_root()
    requirements_path = root / "data/requirements/normalized/major-required-courses-2026.json"
    requirements = json.loads(requirements_path.read_text(encoding="utf-8"))
    assert requirements["cohortAdmissionYear"] == 2026
    departments = json.loads(
        (root / "data/requirements/normalized/department-sources-2026.json").read_text(
            encoding="utf-8"
        )
    )
    catalog = json.loads(
        (root / "apps/web/public/data/catalog-2026-1.json").read_text(encoding="utf-8")
    )

    known_departments = {item["academicUnit"] for item in departments["departments"]}
    catalog_by_code: dict[str, set[str]] = {}
    for section in catalog["sections"]:
        catalog_by_code.setdefault(section["courseCode"], set()).add(normalized(section["name"]))

    programs = requirements["programs"]
    names = [program["academicUnit"] for program in programs]
    assert len(names) == len(set(names))
    assert set(names) == known_departments
    assert sum(bool(program["courses"]) for program in programs) >= 30
    assert sum(len(program["courses"]) for program in programs) >= 100

    for program in programs:
        assert program["status"] in {"AVAILABLE", "MANUAL_REVIEW"}
        if program["status"] == "MANUAL_REVIEW":
            assert program["academicUnit"] == "공학자율학부"
            assert program["manualReviewReason"]
            assert program["handbookPages"] == []
            assert program["courses"] == []
            continue
        assert program["manualReviewReason"] is None
        codes = [course["courseCode"] for course in program["courses"]]
        assert len(codes) == len(set(codes))
        for course in program["courses"]:
            assert course["grade"] in {1, 2, 3, 4}
            assert course["semesters"]
            assert set(course["semesters"]) <= {1, 2}
            assert course["handbookPage"] in program["handbookPages"]
            if course["courseCode"] in catalog_by_code:
                assert normalized(course["name"]) in catalog_by_code[course["courseCode"]]

    packaged = json.loads(
        (root / "apps/web/public/data/major-required-courses-2026.json").read_text(encoding="utf-8")
    )
    assert packaged == requirements
