from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class APIModel(BaseModel):
    """Base API model with a stable camelCase wire contract."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


def normalize_search_text(value: Any) -> str:
    return re.sub(r"\s+", "", str(value)).casefold()
