from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from timetabler.config import repository_root
from timetabler.requirements.normalizer import Word, _pdf_pages, academic_unit_key

FIRST_ADMISSION_YEAR = 2020
LAST_ADMISSION_YEAR = 2026
CURRICULUM_BUNDLE = Path("requirements/normalized/curriculum-requirements-2016-2026.json")
DEFAULT_OUTPUT = Path("requirements/normalized/graduation-requirements-2020-2026.json")
TOTAL_CREDIT_VALUES = {"120", "126", "130"}


@dataclass(frozen=True, slots=True)
class CreditTableSpec:
    page: int
    program_path: str
    centers: Mapping[str, float]


OLD_DOUBLE = {
    "liberalRequiredMin": 224,
    "liberalElectiveMin": 258,
    "liberalRange": 288,
    "majorFoundationMin": 326,
    "majorRequiredMin": 347,
    "majorElectiveMin": 368,
    "primaryMajorMin": 394,
    "secondaryProgramMin": 431,
    "totalCreditsMin": 502,
}
OLD_ADVANCED = {
    "liberalRequiredMin": 224,
    "liberalElectiveMin": 258,
    "liberalRange": 288,
    "majorFoundationMin": 326,
    "majorRequiredMin": 347,
    "majorElectiveMin": 368,
    "additionalMajorMin": 401,
    "primaryMajorMin": 438,
    "totalCreditsMin": 502,
}
NEW_DOUBLE = {
    "liberalRequiredMin": 245,
    "liberalElectiveMin": 267,
    "liberalRange": 286,
    "majorFoundationMin": 324,
    "majorRequiredMin": 347,
    "majorElectiveMin": 366,
    "primaryMajorMin": 392,
    "secondaryProgramMin": 429,
    "totalCreditsMin": 500,
}
NEW_ADDITIONAL = {
    "liberalRequiredMin": 238,
    "liberalElectiveMin": 258,
    "liberalRange": 276,
    "majorFoundationMin": 314,
    "majorRequiredMin": 338,
    "majorElectiveMin": 359,
    "additionalMajorMin": 383,
    "primaryMajorMin": 409,
    "secondaryProgramMin": 446,
    "totalCreditsMin": 509,
}

TABLES: dict[int, tuple[CreditTableSpec, ...]] = {
    2020: (
        CreditTableSpec(
            24,
            "DOUBLE_MAJOR",
            {
                **OLD_DOUBLE,
                "liberalRequiredMin": 216,
                "liberalElectiveMin": 250,
                "liberalRange": 280,
                "majorFoundationMin": 318,
                "majorRequiredMin": 340,
                "majorElectiveMin": 360,
                "primaryMajorMin": 384,
                "secondaryProgramMin": 425,
            },
        ),
        CreditTableSpec(
            25,
            "ADVANCED_MAJOR",
            {
                **OLD_ADVANCED,
                "liberalRequiredMin": 216,
                "liberalElectiveMin": 250,
                "liberalRange": 280,
                "majorFoundationMin": 318,
                "majorRequiredMin": 340,
                "majorElectiveMin": 360,
                "additionalMajorMin": 397,
            },
        ),
    ),
    2021: (
        CreditTableSpec(24, "DOUBLE_MAJOR", OLD_DOUBLE),
        CreditTableSpec(25, "ADVANCED_MAJOR", OLD_ADVANCED),
    ),
    2022: (
        CreditTableSpec(24, "DOUBLE_MAJOR", OLD_DOUBLE),
        CreditTableSpec(25, "ADVANCED_MAJOR", OLD_ADVANCED),
    ),
    2023: (
        CreditTableSpec(25, "DOUBLE_MAJOR", OLD_DOUBLE),
        CreditTableSpec(26, "ADVANCED_MAJOR", OLD_ADVANCED),
    ),
    2024: (
        CreditTableSpec(12, "DOUBLE_MAJOR", OLD_DOUBLE),
        CreditTableSpec(13, "ADVANCED_MAJOR", OLD_ADVANCED),
    ),
    2025: (
        CreditTableSpec(13, "DOUBLE_MAJOR", NEW_DOUBLE),
        CreditTableSpec(14, "MINOR", NEW_ADDITIONAL),
        CreditTableSpec(15, "MICRO_MAJOR", NEW_ADDITIONAL),
        CreditTableSpec(
            16,
            "ADVANCED_MAJOR",
            {key: value for key, value in NEW_ADDITIONAL.items() if key != "secondaryProgramMin"},
        ),
    ),
    2026: (
        CreditTableSpec(13, "DOUBLE_MAJOR", NEW_DOUBLE),
        CreditTableSpec(14, "MINOR", NEW_ADDITIONAL),
        CreditTableSpec(15, "MICRO_MAJOR", NEW_ADDITIONAL),
        CreditTableSpec(
            16,
            "ADVANCED_MAJOR",
            {key: value for key, value in NEW_ADDITIONAL.items() if key != "secondaryProgramMin"},
        ),
    ),
}

LIBERAL_PAGES = {
    2020: 28,
    2021: 27,
    2022: 27,
    2023: 28,
    2024: 15,
    2025: 18,
    2026: 18,
}

LIBERAL_AREAS: dict[int, tuple[tuple[str, int | None], ...]] = {
    2020: (
        ("제1영역:인간과문학", None),
        ("제2영역:역사와철학", None),
        ("제3영역:사회와경제", None),
        ("제4영역:과학과기술", None),
        ("제5영역:예술과문화", None),
    ),
    2021: (
        ("제1영역:인간과문학", None),
        ("제2영역:역사와철학", None),
        ("제3영역:사회와경제", None),
        ("제4영역:과학과기술", None),
        ("제5영역:예술과문화", None),
    ),
    2022: (
        ("제1영역:인간과문학", None),
        ("제2영역:역사와철학", None),
        ("제3영역:사회와경제", None),
        ("제4영역:과학과기술", None),
        ("제5영역:예술과문화", None),
    ),
    2023: (
        ("제1영역:인간과문학", None),
        ("제2영역:역사와철학", None),
        ("제3영역:사회와경제", None),
        ("제4영역:과학과기술", None),
        ("제5영역:예술과문화", None),
    ),
    2024: (
        ("제1영역:인간과문학", None),
        ("제2영역:역사와철학", None),
        ("제3영역:사회와경제", None),
        ("제4영역:과학과기술", None),
        ("제5영역:예술과문화", None),
    ),
    2025: (
        ("제1영역:인간과소통", 2),
        ("제2영역:사회와경제", 2),
        ("제3영역:과학과기술", 2),
        ("제4영역:예술과문화", 2),
        ("제5영역:융합과혁신", 2),
        ("제6영역:디지털리터러시", 2),
    ),
    2026: (
        ("제1영역:인간과소통", 2),
        ("제2영역:사회와경제", 2),
        ("제3영역:과학과기술", 2),
        ("제4영역:예술과문화", 2),
        ("제5영역:융합과혁신", 2),
        ("제6영역:AI·디지털리터러시", 2),
    ),
}

STANDARD_LIBERAL_TOTALS = {
    2020: (12, 24),
    2021: (13, 23),
    2022: (13, 23),
    2023: (13, 23),
    2024: (13, 23),
    2025: (13, 21),
    2026: (11, 21),
}

TRANSITION_MODES = {
    "표준화 자격요건 바로 적용": "STANDARDIZED_ONLY",
    "기존·표준화 자격요건 모두 적용": "LEGACY_OR_STANDARDIZED",
    "기존 자격요건 유지": "LEGACY_ONLY",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected an object: {path}")
    return value


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {key: value.strip() for key, value in row.items()} for row in csv.DictReader(handle)
        ]


def _row_token(words: list[Word], top: float, center: float) -> str | None:
    matches = [word for word in words if abs(word.top - top) < 1.8 and abs(word.left - center) < 13]
    if not matches:
        return None
    return min(matches, key=lambda word: abs(word.left - center)).text


def _credit_value(token: str | None) -> int | None:
    if token is None:
        return None
    if token in {"-", "\uff0d"}:
        return 0
    return int(token) if token.isdigit() else None


def _credit_range(token: str | None) -> tuple[int, int | None]:
    if token is None:
        raise ValueError("credit table row is missing the liberal credit range")
    if token.isdigit():
        return int(token), None
    match = re.fullmatch(r"(\d+)\s*[~\uFF5E-]\s*(\d+)", token)
    if match is None:
        raise ValueError(f"invalid liberal credit range: {token}")
    return int(match.group(1)), int(match.group(2))


def _program_name(
    words: list[Word],
    top: float,
    known_programs: list[tuple[str, dict[str, Any]]],
) -> tuple[str, list[str]]:
    source_name = "".join(
        word.text
        for word in sorted(words, key=lambda word: word.left)
        if 75 <= word.left < 235 and abs(word.top - top) < 2.8
    )
    source_key = academic_unit_key(source_name)
    matches = [program for key, program in known_programs if key and key in source_key]
    if matches:
        program = matches[0]
        aliases = [str(alias) for alias in program["academicUnitAliases"]]
        return str(program["academicUnit"]), aliases
    if source_key == academic_unit_key("공학자율학부"):
        return "공학자율학부", ["공학자율학부"]
    raise ValueError(f"could not map credit table academic unit: {source_name!r}")


def _credit_profile(
    year: int,
    spec: CreditTableSpec,
    words: list[Word],
    top: float,
    known_programs: list[tuple[str, dict[str, Any]]],
    required_courses: list[dict[str, Any]],
) -> dict[str, Any]:
    academic_unit, aliases = _program_name(words, top, known_programs)
    raw_values = {field: _row_token(words, top, center) for field, center in spec.centers.items()}
    liberal_min, liberal_max = _credit_range(raw_values.pop("liberalRange"))
    values = {field: _credit_value(token) for field, token in raw_values.items()}
    for field in (
        "majorFoundationMin",
        "majorRequiredMin",
        "majorElectiveMin",
        "additionalMajorMin",
    ):
        if field in values and values[field] is None:
            values[field] = 0
    if values["totalCreditsMin"] not in {120, 126, 130}:
        raise ValueError(f"invalid total credits for {year} {academic_unit}")
    values["liberalMin"] = liberal_min
    values["liberalMax"] = liberal_max

    consistency_warnings: list[dict[str, Any]] = []
    calculated_primary = sum(
        values.get(field) or 0
        for field in (
            "majorFoundationMin",
            "majorRequiredMin",
            "majorElectiveMin",
            "additionalMajorMin",
        )
    )
    if calculated_primary != values["primaryMajorMin"]:
        consistency_warnings.append(
            {
                "code": "PRIMARY_MAJOR_SUM_MISMATCH",
                "calculated": calculated_primary,
                "printed": values["primaryMajorMin"],
            }
        )

    standard_required, standard_elective = STANDARD_LIBERAL_TOTALS[year]
    liberal_courses = required_courses if values["liberalRequiredMin"] == standard_required else []
    liberal_areas = (
        [
            {"area": area, "minCourses": 1, "minCredits": credits}
            for area, credits in LIBERAL_AREAS[year]
        ]
        if values["liberalElectiveMin"] == standard_elective
        else []
    )
    path_key = spec.program_path.lower().replace("_", "-")
    return {
        "id": f"degree-credit-{year}-{path_key}-{academic_unit_key(academic_unit)}",
        "admissionYears": {"start": year, "end": year},
        "scope": {
            "studentType": "DOMESTIC",
            "academicUnit": academic_unit,
            "programPath": spec.program_path,
        },
        "kind": "DEGREE_CREDIT_PROFILE",
        "academicUnitAliases": aliases,
        "values": values,
        "requiredLiberalCourses": liberal_courses,
        "liberalAreaRequirements": liberal_areas,
        "consistencyWarnings": consistency_warnings,
        "requiresManualReview": bool(consistency_warnings),
        "sourceRefs": [f"curriculum-guide-{year}:pdf-page-{spec.page}"],
    }


def _extract_credit_profiles(
    year: int,
    pages: dict[int, list[Word]],
    programs: list[dict[str, Any]],
    required_courses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    known_programs = sorted(
        ((academic_unit_key(str(program["academicUnit"])), program) for program in programs),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    profiles: dict[str, dict[str, Any]] = {}
    for spec in TABLES[year]:
        words = pages[spec.page]
        total_rows = [
            word
            for word in words
            if word.left > 480 and word.text in TOTAL_CREDIT_VALUES and word.top > 140
        ]
        if len(total_rows) < 40:
            raise ValueError(f"{year} {spec.program_path} found too few credit table rows")
        for total in total_rows:
            profile = _credit_profile(
                year,
                spec,
                words,
                total.top,
                known_programs,
                required_courses,
            )
            existing = profiles.get(str(profile["id"]))
            if existing is not None and existing != profile:
                raise ValueError(f"conflicting duplicate credit profile: {profile['id']}")
            profiles[str(profile["id"])] = profile
    return sorted(profiles.values(), key=lambda rule: str(rule["id"]))


def _required_course_name(words: list[Word], anchor: Word, year: int) -> str:
    minimum_left = 240 if year <= 2024 else 205
    name = " ".join(
        word.text
        for word in sorted(words, key=lambda word: (word.top, word.left))
        if minimum_left < word.left < 390 and abs(word.top - anchor.top) < 7.6
    )
    name = re.sub(r"\s*\[집중이수제\]\s*", " ", name).strip()
    if name.startswith("LCT"):
        return "LCT"
    return "".join(name.split())


def _required_liberal_courses(
    year: int,
    words: list[Word],
) -> list[dict[str, Any]]:
    if year == 2020:
        anchors = [
            word
            for word in words
            if 445 < word.left < 475 and word.text in {"1", "2"} and 150 < word.top < 340
        ]
    else:
        anchors = [
            word
            for word in words
            if word.left > 470 and re.fullmatch(r"\d{6}", word.text) and 140 < word.top < 340
        ]
    expected = {2020: 7, 2021: 8, 2022: 8, 2023: 8, 2024: 8, 2025: 7, 2026: 6}
    if len(anchors) != expected[year]:
        raise ValueError(f"{year} found {len(anchors)} required liberal courses")
    courses: list[dict[str, Any]] = []
    for anchor in anchors:
        credit_word = (
            anchor
            if year == 2020
            else next(
                word
                for word in words
                if 445 < word.left < 475
                and abs(word.top - anchor.top) < 1.8
                and word.text in {"1", "2"}
            )
        )
        grade_word = next(
            (
                word
                for word in words
                if 420 < word.left < 445
                and abs(word.top - anchor.top) < 1.8
                and word.text.isdigit()
            ),
            None,
        )
        semester_word = next(
            (word for word in words if 390 < word.left < 420 and abs(word.top - anchor.top) < 1.8),
            None,
        )
        source_name = _required_course_name(words, anchor, year)
        courses.append(
            {
                "courseCode": anchor.text if year != 2020 else None,
                "name": source_name,
                "aliases": [source_name],
                "credits": int(credit_word.text),
                "grade": int(grade_word.text) if grade_word else None,
                "semesters": (
                    [int(value) for value in semester_word.text.split(",")] if semester_word else []
                ),
                "sourceLocator": {"page": LIBERAL_PAGES[year]},
            }
        )
    return courses


def _fill_course_aliases(courses_by_year: dict[int, list[dict[str, Any]]]) -> None:
    code_by_name: dict[str, str] = {}
    aliases_by_code: dict[str, set[str]] = {}
    for courses in courses_by_year.values():
        for course in courses:
            code = course["courseCode"]
            if code:
                code_by_name[academic_unit_key(str(course["name"]))] = str(code)
                aliases_by_code.setdefault(str(code), set()).add(str(course["name"]))
    for courses in courses_by_year.values():
        for course in courses:
            if course["courseCode"] is None:
                course["courseCode"] = code_by_name.get(academic_unit_key(str(course["name"])))
            code = course["courseCode"]
            if code:
                aliases_by_code.setdefault(str(code), set()).add(str(course["name"]))
                course["aliases"] = sorted(aliases_by_code[str(code)])


def _nonempty(row: dict[str, str], *ignored: str) -> dict[str, str]:
    return {key: value for key, value in row.items() if value and key not in ignored}


def _cohort_mentions(row: dict[str, str]) -> list[dict[str, Any]]:
    text = " ".join(row.values())
    patterns = (
        re.compile(r"(?P<start>\d{2})학번\s*[~\uFF5E-]\s*(?P<end>\d{2})학번"),
        re.compile(r"(?P<end>\d{2})학번\s*(?:까지|이전)"),
        re.compile(r"(?P<start>\d{2})학번\s*(?:부터|이후)"),
        re.compile(r"(?P<year>\d{2})학번"),
    )
    mentions: dict[tuple[int | None, int | None, str], dict[str, Any]] = {}
    covered: list[tuple[int, int]] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            if any(start <= match.start() < end for start, end in covered):
                continue
            groups = match.groupdict()
            start = int(groups["start"]) + 2000 if groups.get("start") else None
            end = int(groups["end"]) + 2000 if groups.get("end") else None
            year = int(groups["year"]) + 2000 if groups.get("year") else None
            if year is not None:
                start = end = year
            expression = match.group(0)
            key = (start, end, expression)
            mentions[key] = {
                "start": start,
                "end": end,
                "expression": expression,
            }
            covered.append(match.span())
    return list(mentions.values())


def _assessment_rules(data_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized = data_root / "requirements/normalized"
    transitions = _csv_rows(normalized / "graduation-transition-2026.csv")
    standardized = _csv_rows(normalized / "graduation-standardized-requirements-2026.csv")
    credentials = _csv_rows(normalized / "graduation-credential-details-2026.csv")
    legacy = _csv_rows(normalized / "graduation-legacy-requirements-2026.csv")

    standardized_by_number: dict[str, list[dict[str, str]]] = {}
    for row in standardized:
        standardized_by_number.setdefault(row["source_number"], []).append(row)
    credentials_by_number: dict[str, list[dict[str, str]]] = {}
    for row in credentials:
        credentials_by_number.setdefault(row["source_number"], []).append(row)

    profiles: list[dict[str, Any]] = []
    for transition in transitions:
        source_number = transition["source_number"]
        academic_unit = transition["academic_unit"]
        categories = []
        for row in standardized_by_number.get(source_number, []):
            categories.append(
                {
                    "code": row["category_code"],
                    "name": row["category_name"],
                    "primaryPolicy": {
                        "none": row["primary_none"] or None,
                        "one": row["primary_one"] or None,
                        "two": row["primary_two"] or None,
                    },
                    "doubleMajorPolicy": {
                        "none": row["double_major_none"] or None,
                        "one": row["double_major_one"] or None,
                    },
                    "requirementDetail": row["requirement_detail"] or None,
                    "referenceNote": row["reference_note"] or None,
                    "sourceNote": row["source_note"] or None,
                }
            )
        profiles.append(
            {
                "id": f"department-assessment-2026-{source_number}",
                "effectiveYear": 2026,
                "scope": {"academicUnit": academic_unit},
                "kind": "DEPARTMENT_ASSESSMENT_PROFILE",
                "values": {
                    "transitionMode": TRANSITION_MODES[transition["transition_2026"]],
                    "transitionSourceText": transition["transition_2026"],
                    "sourceNote": transition["source_note"] or None,
                    "categories": categories,
                    "credentialDetails": [
                        _nonempty(row, "source_row_number", "source_number", "academic_unit")
                        for row in credentials_by_number.get(source_number, [])
                    ],
                },
                "requiresManualReview": True,
                "sourceRefs": [
                    "graduation-transition-2026",
                    "graduation-standardized-requirements-2026",
                    "graduation-credential-details-2026",
                ],
            }
        )

    legacy_rules = [
        {
            "id": f"legacy-department-assessment-2026-{index + 1}",
            "effectiveYear": 2026,
            "scope": {"academicUnit": row["academic_unit"]},
            "kind": "LEGACY_DEPARTMENT_ASSESSMENT",
            "values": {
                "requirements": _nonempty(row, "academic_unit"),
                "cohortMentions": _cohort_mentions(row),
            },
            "requiresManualReview": True,
            "sourceRefs": ["graduation-legacy-requirements-2026"],
        }
        for index, row in enumerate(legacy)
    ]
    return profiles, legacy_rules


def build_bundle(data_root: Path) -> dict[str, Any]:
    resolved_root = data_root.resolve()
    curriculum = _load_json(resolved_root / CURRICULUM_BUNDLE)
    programs_by_year = {
        int(dataset["admissionYear"]): dataset["programs"] for dataset in curriculum["datasets"]
    }
    pages_by_year: dict[int, dict[int, list[Word]]] = {}
    courses_by_year: dict[int, list[dict[str, Any]]] = {}
    sources: list[dict[str, Any]] = []
    for year in range(FIRST_ADMISSION_YEAR, LAST_ADMISSION_YEAR + 1):
        relative_path = f"requirements/raw/{year}/{year}-curriculum-guide.pdf"
        source_path = resolved_root / relative_path
        pages = _pdf_pages(source_path)
        pages_by_year[year] = pages
        courses_by_year[year] = _required_liberal_courses(year, pages[LIBERAL_PAGES[year]])
        sources.append(
            {
                "id": f"curriculum-guide-{year}",
                "path": relative_path,
                "sha256": _sha256(source_path),
            }
        )
    _fill_course_aliases(courses_by_year)

    rules: list[dict[str, Any]] = []
    credit_counts: dict[str, int] = {}
    for year in range(FIRST_ADMISSION_YEAR, LAST_ADMISSION_YEAR + 1):
        profiles = _extract_credit_profiles(
            year,
            pages_by_year[year],
            programs_by_year[year],
            courses_by_year[year],
        )
        rules.extend(profiles)
        credit_counts[str(year)] = len(profiles)

    assessment_profiles, legacy_rules = _assessment_rules(resolved_root)
    rules.extend(assessment_profiles)
    rules.extend(legacy_rules)
    for filename in (
        "graduation-transition-2026.csv",
        "graduation-standardized-requirements-2026.csv",
        "graduation-legacy-requirements-2026.csv",
        "graduation-credential-details-2026.csv",
    ):
        path = resolved_root / "requirements/normalized" / filename
        sources.append(
            {
                "id": filename.removesuffix(".csv"),
                "path": f"requirements/normalized/{filename}",
                "sha256": _sha256(path),
            }
        )

    payload = {
        "schemaVersion": 1,
        "asOf": "2026-07-18",
        "admissionYearRange": {
            "start": FIRST_ADMISSION_YEAR,
            "end": LAST_ADMISSION_YEAR,
        },
        "sources": sources,
        "requiredLiberalCoursesByYear": {
            str(year): courses for year, courses in courses_by_year.items()
        },
        "rules": rules,
        "summary": {
            "degreeCreditProfiles": sum(credit_counts.values()),
            "degreeCreditProfilesByYear": credit_counts,
            "departmentAssessmentProfiles": len(assessment_profiles),
            "legacyDepartmentAssessmentRules": len(legacy_rules),
            "rules": len(rules),
        },
    }
    validate_bundle(payload)
    return payload


def validate_bundle(payload: dict[str, Any]) -> None:
    years = payload.get("admissionYearRange", {})
    if years != {"start": FIRST_ADMISSION_YEAR, "end": LAST_ADMISSION_YEAR}:
        raise ValueError("unexpected graduation requirement admission year range")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        raise ValueError("graduation requirement rules must be objects")
    rule_ids = [str(rule["id"]) for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ValueError("graduation requirement rules contain duplicate ids")
    source_ids = {str(source["id"]) for source in payload.get("sources", [])}
    unknown_source_refs = {
        str(source_ref).split(":", 1)[0]
        for rule in rules
        for source_ref in rule.get("sourceRefs", [])
        if str(source_ref).split(":", 1)[0] not in source_ids
    }
    if unknown_source_refs:
        unknown = ", ".join(sorted(unknown_source_refs))
        raise ValueError(f"graduation requirement rules reference unknown sources: {unknown}")
    degree_rules = [rule for rule in rules if rule["kind"] == "DEGREE_CREDIT_PROFILE"]
    years_found = {int(rule["admissionYears"]["start"]) for rule in degree_rules}
    if years_found != set(range(FIRST_ADMISSION_YEAR, LAST_ADMISSION_YEAR + 1)):
        raise ValueError("degree credit profiles do not cover every admission year")
    if any(rule["values"].get("totalCreditsMin") not in {120, 126, 130} for rule in degree_rules):
        raise ValueError("degree credit profile has an invalid total credit minimum")
    assessments = [rule for rule in rules if rule["kind"] == "DEPARTMENT_ASSESSMENT_PROFILE"]
    if len(assessments) != 66 or any(
        len(rule["values"]["categories"]) != 4 for rule in assessments
    ):
        raise ValueError("department assessment profile coverage is incomplete")
    legacy = [rule for rule in rules if rule["kind"] == "LEGACY_DEPARTMENT_ASSESSMENT"]
    if len(legacy) != 35:
        raise ValueError("legacy department assessment coverage is incomplete")
    required_by_year = payload.get("requiredLiberalCoursesByYear", {})
    expected_counts = {"2020": 7, "2021": 8, "2022": 8, "2023": 8, "2024": 8, "2025": 7, "2026": 6}
    if {year: len(courses) for year, courses in required_by_year.items()} != expected_counts:
        raise ValueError("required liberal course coverage is incomplete")


def write_bundle(data_root: Path, output: Path | None = None) -> Path:
    resolved_root = data_root.resolve()
    destination = output.resolve() if output else resolved_root / DEFAULT_OUTPUT
    payload = build_bundle(resolved_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def run() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=repository_root() / "data")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    destination = write_bundle(arguments.data_root, arguments.output)
    print(destination)


if __name__ == "__main__":
    run()
