from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from timetabler.config import repository_root

FIRST_ADMISSION_YEAR = 2016
LAST_ADMISSION_YEAR = 2026
REQUIRED_CLASSIFICATIONS = {"전기", "전필"}
ALL_CLASSIFICATIONS = {"전기", "전필", "전선"}
COURSE_CODE = re.compile(r"\d{6}")
DEFAULT_OUTPUT = Path("requirements/normalized/curriculum-requirements-2016-2026.json")


@dataclass(frozen=True, slots=True)
class Word:
    text: str
    left: float
    top: float


@dataclass(frozen=True, slots=True)
class PdfCourseRow:
    top: float
    code: str
    name: str
    credits: float | None
    semesters: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class HwpCell:
    row: int
    column: int
    rowspan: int
    colspan: int
    text: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def academic_unit_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(character.casefold() for character in normalized if character.isalnum())


def _float(value: str) -> float | None:
    normalized = value.strip()
    if not normalized or not re.fullmatch(r"\d+(?:\.\d+)?", normalized):
        return None
    return float(normalized)


def _pdf_pages(pdf: Path) -> dict[int, list[Word]]:
    completed = subprocess.run(
        ["pdftotext", "-tsv", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    reader = csv.DictReader(StringIO(completed.stdout), delimiter="\t")
    pages: dict[int, list[Word]] = defaultdict(list)
    for row in reader:
        if row["level"] != "5":
            continue
        pages[int(row["page_num"])].append(
            Word(text=row["text"], left=float(row["left"]), top=float(row["top"]))
        )
    return dict(pages)


def _page_title(words: list[Word]) -> str:
    title_words = sorted(
        (word for word in words if 20 <= word.top <= 48 and 100 <= word.left <= 480),
        key=lambda word: word.left,
    )
    return _compact_text(" ".join(word.text for word in title_words))


def _pdf_course_rows(words: list[Word]) -> list[PdfCourseRow]:
    rows: list[PdfCourseRow] = []
    for code in words:
        if not COURSE_CODE.fullmatch(code.text) or not (
            80 < code.left < 145 and 80 < code.top < 790
        ):
            continue
        on_row = sorted(
            (word for word in words if abs(word.top - code.top) < 1),
            key=lambda word: word.left,
        )
        name = _compact_text(" ".join(word.text for word in on_row if 140 < word.left < 330))
        if not name:
            continue
        first_values = [
            word for word in on_row if 330 < word.left < 430 and _float(word.text) is not None
        ]
        second_values = [
            word for word in on_row if 450 < word.left < 550 and _float(word.text) is not None
        ]
        semesters = tuple(
            semester for semester, values in ((1, first_values), (2, second_values)) if values
        )
        credit_word = next(iter(first_values or second_values), None)
        rows.append(
            PdfCourseRow(
                top=code.top,
                code=code.text,
                name=name,
                credits=_float(credit_word.text) if credit_word else None,
                semesters=semesters,
            )
        )
    return sorted(rows, key=lambda row: row.top)


def _labels(
    words: list[Word],
    allowed: set[str],
    *,
    maximum_left: float,
) -> list[tuple[float, str]]:
    return sorted(
        (
            (word.top, word.text)
            for word in words
            if word.text in allowed and word.left < maximum_left and word.top > 80
        ),
        key=lambda item: item[0],
    )


def _assign_merged_groups[T](
    rows: list[PdfCourseRow], group_labels: list[tuple[float, T]]
) -> dict[str, T]:
    row_count = len(rows)
    label_count = len(group_labels)
    if not rows or not group_labels or label_count > row_count:
        return {}

    infinity = float("inf")
    costs = [[infinity] * (row_count + 1) for _ in range(label_count + 1)]
    previous: list[list[int | None]] = [[None] * (row_count + 1) for _ in range(label_count + 1)]
    costs[0][0] = 0

    for label_index in range(1, label_count + 1):
        label_top = group_labels[label_index - 1][0]
        for end in range(label_index, row_count - (label_count - label_index) + 1):
            for start in range(label_index - 1, end):
                if costs[label_index - 1][start] == infinity:
                    continue
                centre = (rows[start].top + rows[end - 1].top) / 2
                span = max(15, rows[end - 1].top - rows[start].top + 15)
                candidate = costs[label_index - 1][start] + ((label_top - centre) / span) ** 2
                if candidate < costs[label_index][end]:
                    costs[label_index][end] = candidate
                    previous[label_index][end] = start

    partitions: list[tuple[int, int]] = []
    end = row_count
    for label_index in range(label_count, 0, -1):
        partition_start = previous[label_index][end]
        if partition_start is None:
            return {}
        partitions.append((partition_start, end))
        end = partition_start
    partitions.reverse()

    assigned: dict[str, T] = {}
    for (_, label), (start, end) in zip(group_labels, partitions, strict=True):
        for row in rows[start:end]:
            assigned[row.code] = label
    return assigned


def _program_payload(
    academic_unit: str,
    source_locators: list[dict[str, Any]],
    source_course_count: int,
    courses: list[dict[str, Any]],
) -> dict[str, Any]:
    unique_courses: dict[tuple[str, str], dict[str, Any]] = {}
    for course in courses:
        unique_courses[(str(course["classification"]), str(course["courseCode"]))] = course
    ordered_courses = sorted(
        unique_courses.values(),
        key=lambda item: (
            int(item["grade"]) if item["grade"] is not None else 99,
            tuple(item["semesters"]),
            str(item["classification"]),
            str(item["courseCode"]),
        ),
    )
    return {
        "academicUnit": academic_unit,
        "academicUnitKey": academic_unit_key(academic_unit),
        "academicUnitAliases": [academic_unit],
        "status": "AVAILABLE",
        "sourceLocators": source_locators,
        "sourceCourseCount": source_course_count,
        "requiredCourses": ordered_courses,
    }


def _apply_reviewed_2026_aliases(data_root: Path, programs: list[dict[str, Any]]) -> None:
    reviewed_path = data_root / "requirements/normalized/major-required-courses-2026.json"
    reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
    by_key = {str(program["academicUnitKey"]): program for program in programs}
    for reviewed_program in reviewed["programs"]:
        if reviewed_program["status"] != "AVAILABLE":
            continue
        reviewed_name = str(reviewed_program["academicUnit"])
        candidate = by_key.get(academic_unit_key(reviewed_name))
        if candidate is None and reviewed_name.endswith(" 공통"):
            candidate = by_key.get(academic_unit_key(reviewed_name.removesuffix(" 공통")))
        if candidate is None:
            reviewed_pages = {int(page) for page in reviewed_program["handbookPages"]}
            page_matches = [
                program
                for program in programs
                if reviewed_pages
                & {
                    int(locator["page"])
                    for locator in program["sourceLocators"]
                    if "page" in locator
                }
            ]
            if len(page_matches) == 1:
                candidate = page_matches[0]
        if candidate is None:
            raise ValueError(f"reviewed 2026 unit was not extracted: {reviewed_name}")
        aliases = candidate["academicUnitAliases"]
        alias_keys = {academic_unit_key(str(alias)) for alias in aliases}
        if academic_unit_key(reviewed_name) not in alias_keys:
            aliases.append(reviewed_name)
        expected = {
            (str(course["courseCode"]), str(course["name"]))
            for course in reviewed_program["courses"]
        }
        actual = {
            (str(course["courseCode"]), str(course["name"]))
            for course in candidate["requiredCourses"]
            if course["classification"] == "전필"
        }
        if expected != actual:
            raise ValueError(f"reviewed 2026 course mismatch for {reviewed_name}")


def _normalize_pdf(year: int, pdf: Path) -> list[dict[str, Any]]:
    label_limit = 110 if year == 2017 else 90
    grade_limit = 90 if year == 2017 else 55
    programs: dict[str, dict[str, Any]] = {}
    for page, words in sorted(_pdf_pages(pdf).items()):
        rows = _pdf_course_rows(words)
        classifications = _labels(words, ALL_CLASSIFICATIONS, maximum_left=label_limit)
        title = _page_title(words)
        if not rows or not classifications or not title:
            continue
        assigned_classifications = _assign_merged_groups(rows, classifications)
        assigned_grades = _assign_merged_groups(
            rows,
            _labels(words, {"1", "2", "3", "4"}, maximum_left=grade_limit),
        )
        if len(assigned_classifications) != len(rows):
            raise ValueError(f"could not classify every {year} curriculum row on page {page}")
        key = academic_unit_key(title)
        program = programs.setdefault(
            key,
            {
                "academicUnit": title,
                "sourceLocators": [],
                "sourceCourseCount": 0,
                "requiredCourses": [],
            },
        )
        program["sourceLocators"].append({"page": page})
        program["sourceCourseCount"] += len(rows)
        for row in rows:
            classification = assigned_classifications[row.code]
            if classification not in REQUIRED_CLASSIFICATIONS:
                continue
            program["requiredCourses"].append(
                {
                    "classification": classification,
                    "courseCode": row.code,
                    "name": row.name,
                    "credits": row.credits,
                    "grade": (
                        int(assigned_grades[row.code]) if row.code in assigned_grades else None
                    ),
                    "semesters": list(row.semesters),
                    "sourceLocator": {"page": page},
                }
            )
    return sorted(
        (
            _program_payload(
                str(program["academicUnit"]),
                list(program["sourceLocators"]),
                int(program["sourceCourseCount"]),
                list(program["requiredCourses"]),
            )
            for program in programs.values()
        ),
        key=lambda item: str(item["academicUnitKey"]),
    )


def _hwp_cells(table_body: ET.Element) -> list[HwpCell]:
    cells: list[HwpCell] = []
    for cell in table_body.findall(".//TableCell"):
        cells.append(
            HwpCell(
                row=int(cell.attrib["row"]),
                column=int(cell.attrib["col"]),
                rowspan=int(cell.attrib.get("rowspan", "1")),
                colspan=int(cell.attrib.get("colspan", "1")),
                text=_compact_text("".join(cell.itertext())),
            )
        )
    return cells


def _matrix(cells: list[HwpCell]) -> dict[tuple[int, int], str]:
    result: dict[tuple[int, int], str] = {}
    for cell in cells:
        for row in range(cell.row, cell.row + cell.rowspan):
            for column in range(cell.column, cell.column + cell.colspan):
                result[(row, column)] = cell.text
    return result


def _header(cells: list[HwpCell], text: str) -> HwpCell:
    try:
        return next(cell for cell in cells if cell.text == text)
    except StopIteration as exc:
        raise ValueError(f"2016 HWP curriculum table is missing the {text!r} header") from exc


def _normalize_hwp_2016(hwp: Path) -> list[dict[str, Any]]:
    executable = shutil.which("hwp5proc")
    if executable is None:
        raise RuntimeError("hwp5proc is required to normalize the 2016 HWP handbook")
    completed = subprocess.run(
        [executable, "xml", "--format", "nested", str(hwp)],
        check=True,
        capture_output=True,
    )
    root = ET.fromstring(completed.stdout)
    programs: dict[str, dict[str, Any]] = {}
    for table in root.findall(".//TableControl"):
        body = table.find(".//TableBody")
        if body is None:
            continue
        cells = _hwp_cells(body)
        cell_texts = {cell.text for cell in cells}
        if not {"이수구분", "교과번호", "교과목명"}.issubset(cell_texts):
            continue
        title = _compact_text(
            " / ".join(cell.text for cell in cells if cell.row == 0 and cell.text)
        )
        if not title:
            continue
        classification_header = _header(cells, "이수구분")
        code_header = _header(cells, "교과번호")
        name_header = _header(cells, "교과목명")
        grade_header = _header(cells, "학년")
        first_semester = _header(cells, "1학기")
        second_semester = _header(cells, "2학기")
        first_data_row = max(
            header.row + header.rowspan
            for header in (classification_header, code_header, name_header, grade_header)
        )
        values = _matrix(cells)
        table_id = str(table.attrib["table-id"])
        key = academic_unit_key(title)
        program = programs.setdefault(
            key,
            {
                "academicUnit": title,
                "sourceLocators": [],
                "sourceCourseCount": 0,
                "requiredCourses": [],
            },
        )
        program["sourceLocators"].append({"tableId": table_id})
        for row_number in range(first_data_row, int(body.attrib["rows"])):
            code = values.get((row_number, code_header.column), "")
            if not COURSE_CODE.fullmatch(code):
                continue
            program["sourceCourseCount"] += 1
            classification = values.get((row_number, classification_header.column), "")
            if classification not in REQUIRED_CLASSIFICATIONS:
                continue
            first_credits = _float(values.get((row_number, first_semester.column), ""))
            second_credits = _float(values.get((row_number, second_semester.column), ""))
            semesters = [
                semester
                for semester, credits in ((1, first_credits), (2, second_credits))
                if credits is not None
            ]
            grade = values.get((row_number, grade_header.column), "")
            program["requiredCourses"].append(
                {
                    "classification": classification,
                    "courseCode": code,
                    "name": values.get((row_number, name_header.column), ""),
                    "credits": first_credits if first_credits is not None else second_credits,
                    "grade": int(grade) if grade in {"1", "2", "3", "4"} else None,
                    "semesters": semesters,
                    "sourceLocator": {"tableId": table_id},
                }
            )
    return sorted(
        (
            _program_payload(
                str(program["academicUnit"]),
                list(program["sourceLocators"]),
                int(program["sourceCourseCount"]),
                list(program["requiredCourses"]),
            )
            for program in programs.values()
        ),
        key=lambda item: str(item["academicUnitKey"]),
    )


def _rule_sources(data_root: Path) -> list[dict[str, Any]]:
    definitions = (
        (
            "common-graduation-rules",
            "COMMON_RULES",
            None,
            "requirements/normalized/common-graduation-rules.json",
        ),
        (
            "graduation-transition-2026",
            "GRADUATION_TRANSITION",
            2026,
            "requirements/normalized/graduation-transition-2026.csv",
        ),
        (
            "graduation-standardized-2026",
            "GRADUATION_STANDARDIZED",
            2026,
            "requirements/normalized/graduation-standardized-requirements-2026.csv",
        ),
        (
            "graduation-legacy-2026",
            "GRADUATION_LEGACY",
            2026,
            "requirements/normalized/graduation-legacy-requirements-2026.csv",
        ),
        (
            "graduation-credentials-2026",
            "GRADUATION_CREDENTIALS",
            2026,
            "requirements/normalized/graduation-credential-details-2026.csv",
        ),
    )
    return [
        {
            "id": source_id,
            "kind": kind,
            "effectiveYear": effective_year,
            "path": path,
            "sha256": _sha256(data_root / path),
        }
        for source_id, kind, effective_year, path in definitions
    ]


def build_bundle(data_root: Path) -> dict[str, Any]:
    resolved_root = data_root.resolve()
    datasets: list[dict[str, Any]] = []
    for year in range(FIRST_ADMISSION_YEAR, LAST_ADMISSION_YEAR + 1):
        suffix = "hwp" if year == 2016 else "pdf"
        relative_path = f"requirements/raw/{year}/{year}-curriculum-guide.{suffix}"
        source_path = resolved_root / relative_path
        programs = (
            _normalize_hwp_2016(source_path) if year == 2016 else _normalize_pdf(year, source_path)
        )
        if year == 2026:
            _apply_reviewed_2026_aliases(resolved_root, programs)
        datasets.append(
            {
                "id": f"curriculum-requirements-{year}",
                "kind": "CURRICULUM_REQUIREMENTS",
                "admissionYear": year,
                "source": {
                    "path": relative_path,
                    "sha256": _sha256(source_path),
                    "format": suffix.upper(),
                },
                "extractionMethod": (
                    "hwp5-nested-xml-table-cells" if year == 2016 else "poppler-tsv-coordinates"
                ),
                "programCount": len(programs),
                "requiredCourseCount": sum(len(item["requiredCourses"]) for item in programs),
                "programs": programs,
            }
        )
    return {
        "schemaVersion": 1,
        "asOf": "2026-07-17",
        "admissionYearRange": {
            "start": FIRST_ADMISSION_YEAR,
            "end": LAST_ADMISSION_YEAR,
        },
        "datasets": datasets,
        "ruleSources": _rule_sources(resolved_root),
    }


def validate_bundle(payload: dict[str, Any]) -> None:
    years = [int(item["admissionYear"]) for item in payload["datasets"]]
    expected_years = list(range(FIRST_ADMISSION_YEAR, LAST_ADMISSION_YEAR + 1))
    if years != expected_years:
        raise ValueError(f"unexpected admission years: {years}")
    for dataset in payload["datasets"]:
        year = int(dataset["admissionYear"])
        programs = dataset["programs"]
        if len(programs) < 30:
            raise ValueError(f"{year} normalization found too few programs: {len(programs)}")
        if int(dataset["requiredCourseCount"]) < 100:
            raise ValueError(f"{year} normalization found too few required courses")
        keys = [str(item["academicUnitKey"]) for item in programs]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{year} normalization produced duplicate academic units")
        for program in programs:
            course_keys = [
                (str(item["classification"]), str(item["courseCode"]))
                for item in program["requiredCourses"]
            ]
            if len(course_keys) != len(set(course_keys)):
                raise ValueError(
                    f"{year} {program['academicUnit']} contains duplicate required courses"
                )
            if any(
                item["classification"] not in REQUIRED_CLASSIFICATIONS
                for item in program["requiredCourses"]
            ):
                raise ValueError(f"{year} {program['academicUnit']} has an invalid classification")


def write_bundle(data_root: Path, output: Path | None = None) -> Path:
    resolved_root = data_root.resolve()
    destination = output.resolve() if output else resolved_root / DEFAULT_OUTPUT
    payload = build_bundle(resolved_root)
    validate_bundle(payload)
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
