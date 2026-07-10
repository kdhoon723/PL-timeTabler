import pytest
from pydantic import ValidationError

from timetabler.catalog.models import Session
from timetabler.catalog.parser import LectureTimeParseError, parse_lecture_time, time_to_minute


def test_parse_empty_time_as_tba() -> None:
    assert parse_lecture_time("") == ()
    assert parse_lecture_time(None) == ()


def test_parse_multiple_and_irregular_sessions() -> None:
    parsed = parse_lecture_time("월18:25-19:15,토21:20-22:10")

    assert [(item.day, item.start_minute, item.end_minute) for item in parsed] == [
        ("월", 1105, 1155),
        ("토", 1280, 1330),
    ]


@pytest.mark.parametrize("value", ["월09:30", "X09:30-11:00", "월11:00-09:30", "월24:00-25:00"])
def test_reject_invalid_lecture_time(value: str) -> None:
    with pytest.raises((LectureTimeParseError, ValidationError)):
        parse_lecture_time(value)


def test_half_open_adjacency_is_representable_without_overlap() -> None:
    first = Session(day="화", start_minute=570, end_minute=660)
    second = Session(day="화", start_minute=660, end_minute=750)

    assert first.end_minute == second.start_minute
    assert not (first.start_minute < second.end_minute and second.start_minute < first.end_minute)


def test_time_to_minute_preserves_non_slot_times() -> None:
    assert time_to_minute("19:40") == 1180
