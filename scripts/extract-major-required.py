#!/usr/bin/env python3
"""Extract the 2026 major-required curriculum rows from the official handbook.

The handbook uses vertically merged cells for grade and course classification.
Poppler exposes only the text coordinates, so this script reconstructs each
merged group by partitioning the ordered course rows around the printed label
centres.  The generated JSON is intentionally source-oriented: the live course
catalog remains the authority for whether a course is offered this semester.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = ROOT / "data/requirements/raw/2026/2026-curriculum-guide.pdf"
DEFAULT_SOURCES = ROOT / "data/requirements/normalized/department-sources-2026.json"
DEFAULT_OUTPUT = ROOT / "data/requirements/normalized/major-required-courses-2026.json"
CLASSIFICATIONS = {"전기", "전필", "전선"}
COURSE_CODE = re.compile(r"\d{6}")
MANUAL_REVIEW_UNITS = {"공학자율학부"}


@dataclass(frozen=True)
class Word:
    text: str
    left: float
    top: float


@dataclass(frozen=True)
class CourseRow:
    top: float
    code: str
    name: str
    semesters: tuple[int, ...]


def normalized_title(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("(야)", "")
    return "".join(char for char in value if char.isalnum())


def page_words(pdf: Path, page: int) -> list[Word]:
    completed = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), "-tsv", str(pdf), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    reader = csv.DictReader(StringIO(completed.stdout), delimiter="\t")
    return [
        Word(row["text"], float(row["left"]), float(row["top"]))
        for row in reader
        if row["level"] == "5"
    ]


def page_title(words: list[Word]) -> str:
    title_words = sorted(
        (word for word in words if 20 <= word.top <= 48 and 100 <= word.left <= 480),
        key=lambda word: word.left,
    )
    return " ".join(word.text for word in title_words)


def course_rows(words: list[Word]) -> list[CourseRow]:
    rows: list[CourseRow] = []
    for code in words:
        if not COURSE_CODE.fullmatch(code.text) or not (
            80 < code.left < 145 and 80 < code.top < 790
        ):
            continue
        on_row = [word for word in words if abs(word.top - code.top) < 1]
        name = " ".join(
            word.text
            for word in sorted(on_row, key=lambda word: word.left)
            if 140 < word.left < 330
        )
        if not name:
            continue
        first_semester = any(
            330 < word.left < 430 and word.text.replace(".", "", 1).isdigit() for word in on_row
        )
        second_semester = any(
            450 < word.left < 550 and word.text.replace(".", "", 1).isdigit() for word in on_row
        )
        semesters = tuple(
            value for value, present in ((1, first_semester), (2, second_semester)) if present
        )
        rows.append(CourseRow(code.top, code.text, name, semesters))
    return sorted(rows, key=lambda row: row.top)


def labels(
    words: list[Word],
    allowed: set[str],
    *,
    maximum_left: float,
    minimum_top: float = 80,
) -> list[tuple[float, str]]:
    return sorted(
        (
            (word.top, word.text)
            for word in words
            if word.text in allowed and word.left < maximum_left and word.top > minimum_top
        ),
        key=lambda item: item[0],
    )


def assign_merged_groups[T](
    rows: list[CourseRow], group_labels: list[tuple[float, T]]
) -> dict[str, T]:
    """Assign contiguous rows to labels whose glyph is centred in a merged cell."""

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
        start = previous[label_index][end]
        if start is None:
            return {}
        partitions.append((start, end))
        end = start
    partitions.reverse()

    assigned: dict[str, T] = {}
    for (_, label), (start, end) in zip(group_labels, partitions, strict=True):
        for row in rows[start:end]:
            assigned[row.code] = label
    return assigned


def find_page(pdf: Path, academic_unit: str) -> int | None:
    expected = normalized_title(academic_unit)
    for page in range(30, 111):
        title = normalized_title(page_title(page_words(pdf, page)))
        if title and (
            title == expected or title.startswith(expected) or expected.startswith(title)
        ):
            return page
    return None


def program_pages(pdf: Path, start_page: int) -> list[tuple[int, list[Word]]]:
    first_words = page_words(pdf, start_page)
    title = normalized_title(page_title(first_words))
    pages = [(start_page, first_words)]
    for page in range(start_page + 1, min(start_page + 4, 134)):
        words = page_words(pdf, page)
        if not title or normalized_title(page_title(words)) != title:
            break
        pages.append((page, words))
    return pages


def extract_program(pdf: Path, academic_unit: str, start_page: int) -> dict[str, object]:
    extracted: list[dict[str, object]] = []
    handbook_pages: list[int] = []
    for page, words in program_pages(pdf, start_page):
        rows = course_rows(words)
        classification = assign_merged_groups(
            rows,
            labels(words, CLASSIFICATIONS, maximum_left=90),
        )
        grades = assign_merged_groups(
            rows,
            labels(words, {"1", "2", "3", "4"}, maximum_left=55),
        )
        handbook_pages.append(page)
        for row in rows:
            if classification.get(row.code) != "전필":
                continue
            extracted.append(
                {
                    "courseCode": row.code,
                    "name": row.name,
                    "grade": int(grades[row.code]) if row.code in grades else None,
                    "semesters": list(row.semesters),
                    "handbookPage": page,
                }
            )
    return {
        "academicUnit": academic_unit,
        "status": "AVAILABLE",
        "manualReviewReason": None,
        "handbookPages": handbook_pages,
        "courses": extracted,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    sources = json.loads(args.sources.read_text(encoding="utf-8"))
    programs: list[dict[str, object]] = []
    for department in sources["departments"]:
        if department["academicUnit"] in MANUAL_REVIEW_UNITS:
            programs.append(
                {
                    "academicUnit": department["academicUnit"],
                    "status": "MANUAL_REVIEW",
                    "manualReviewReason": department["transitionNote"],
                    "handbookPages": [],
                    "courses": [],
                }
            )
            continue
        start_page = department.get("handbookPage") or find_page(
            args.pdf, department["academicUnit"]
        )
        if start_page is None:
            raise RuntimeError(
                f"No handbook page found for non-allowlisted unit: {department['academicUnit']}"
            )
        programs.append(extract_program(args.pdf, department["academicUnit"], int(start_page)))

    payload = {
        "schemaVersion": 1,
        "asOf": sources["asOf"],
        "cohortAdmissionYear": 2026,
        "source": sources["source"],
        "method": "official-handbook-coordinate-extraction-reviewed-against-merged-cells",
        "programs": programs,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
