from __future__ import annotations

import json

from timetabler.api.app import create_app
from timetabler.config import repository_root


def generate_openapi() -> str:
    document = create_app().openapi()
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def run() -> None:
    destination = repository_root() / "contracts" / "openapi.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(generate_openapi(), encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    run()
