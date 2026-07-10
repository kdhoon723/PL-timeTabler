from __future__ import annotations

import re

from timetabler.catalog.models import Session

_SESSION_PATTERN = re.compile(
    r"^(?P<day>[월화수목금토일])"
    r"(?P<start>\d{1,2}:\d{2})-(?P<end>\d{1,2}:\d{2})$"
)


class LectureTimeParseError(ValueError):
    pass


def time_to_minute(value: str) -> int:
    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        hour, minute = int(hour_text), int(minute_text)
    except (TypeError, ValueError) as exc:
        raise LectureTimeParseError(f"invalid time: {value!r}") from exc
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise LectureTimeParseError(f"invalid time: {value!r}")
    return hour * 60 + minute


def parse_lecture_time(value: str | None) -> tuple[Session, ...]:
    if value is None or not value.strip():
        return ()

    parsed: list[Session] = []
    for raw_part in value.split(","):
        part = raw_part.strip()
        match = _SESSION_PATTERN.fullmatch(part)
        if match is None:
            raise LectureTimeParseError(f"invalid lecture time segment: {part!r}")
        parsed.append(
            Session(
                day=match.group("day"),  # type: ignore[arg-type]
                start_minute=time_to_minute(match.group("start")),
                end_minute=time_to_minute(match.group("end")),
            )
        )
    return tuple(parsed)
