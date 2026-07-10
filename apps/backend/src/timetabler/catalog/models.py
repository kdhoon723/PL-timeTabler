from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from timetabler.types import APIModel

Day = Literal["월", "화", "수", "목", "금", "토", "일"]


class Session(APIModel):
    day: Day
    start_minute: int = Field(ge=0, lt=24 * 60)
    end_minute: int = Field(gt=0, le=24 * 60)
    room_code: str | None = None
    room_name: str | None = None
    building_code: str | None = None
    building_name: str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> Session:
        if self.end_minute <= self.start_minute:
            raise ValueError("session end must be after start")
        return self


class Section(APIModel):
    id: str
    course_code: str
    section_code: str
    name: str
    professor: str | None
    category: str
    credits: float = Field(gt=0)
    raw_lecture_time: str
    sessions: tuple[Session, ...]
    time_to_be_announced: bool
    room_to_be_announced: bool
    warning_codes: tuple[str, ...] = ()


class Semester(APIModel):
    id: str
    prepared_at: str
    dataset_version: str
    section_count: int
    is_active: bool = True


class CatalogPage(APIModel):
    semester: str
    prepared_at: str
    dataset_version: str
    total: int
    offset: int
    limit: int
    sections: tuple[Section, ...]


@dataclass(frozen=True, slots=True)
class CatalogStats:
    course_records: int
    room_records: int
    classroom_sessions: int
    classroom_section_keys: int
    matched_sections: int


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    semester: str
    prepared_at: str
    dataset_version: str
    sections: tuple[Section, ...]
    stats: CatalogStats
