from timetabler.api.openapi import generate_openapi
from timetabler.config import repository_root


def test_openapi_snapshot_is_current() -> None:
    snapshot_path = repository_root() / "contracts" / "openapi.json"
    assert snapshot_path.read_text(encoding="utf-8") == generate_openapi()
