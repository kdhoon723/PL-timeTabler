from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from timetabler.api.app import create_app
from timetabler.api.rate_limit import SlidingWindowRateLimiter, client_key_from_headers
from timetabler.config import Settings


async def test_sliding_window_prunes_expired_unique_client_keys() -> None:
    current = [0.0]
    limiter = SlidingWindowRateLimiter(
        limit=1,
        window_seconds=10,
        clock=lambda: current[0],
    )
    await limiter.consume("198.51.100.1")
    assert "198.51.100.1" in limiter._events

    current[0] = 11
    await limiter.consume("198.51.100.2")

    assert "198.51.100.1" not in limiter._events
    assert set(limiter._events) == {"198.51.100.2"}


def test_client_identity_uses_cloudflare_header_then_peer() -> None:
    assert client_key_from_headers("203.0.113.9", "internal-nginx") == "203.0.113.9"
    assert client_key_from_headers("  ", "internal-nginx") == "internal-nginx"
    assert client_key_from_headers(None, "internal-nginx") == "internal-nginx"
    assert client_key_from_headers(None, None) == "local-unknown"


def _optimizer_payload(client: TestClient) -> dict[str, object]:
    semester = client.get("/api/v1/semesters").json()[0]
    return {
        "semester": semester["id"],
        "datasetVersion": semester["datasetVersion"],
        "minCredits": 0,
        "maxCredits": 18,
    }


def _custom_settings(settings: Settings, tmp_path: Path, **updates: object) -> Settings:
    return settings.model_copy(
        update={
            "database_url": f"sqlite+aiosqlite:///{tmp_path / 'rate-limit.db'}",
            **updates,
        }
    )


def test_optimizer_post_rate_limits_each_cloudflare_client(
    settings: Settings, tmp_path: Path
) -> None:
    configured = _custom_settings(
        settings,
        tmp_path,
        optimization_rate_limit_requests=1,
        optimization_rate_limit_window_seconds=60,
        optimization_active_job_limit=10,
    )
    with TestClient(create_app(configured)) as client:
        payload = _optimizer_payload(client)
        first = client.post(
            "/api/v1/optimizations",
            json=payload,
            headers={"CF-Connecting-IP": "203.0.113.1"},
        )
        repeated = client.post(
            "/api/v1/optimizations",
            json=payload,
            headers={"CF-Connecting-IP": "203.0.113.1"},
        )
        other_client = client.post(
            "/api/v1/optimizations",
            json=payload,
            headers={"CF-Connecting-IP": "203.0.113.2"},
        )

    assert first.status_code == 202
    assert repeated.status_code == 429
    assert int(repeated.headers["Retry-After"]) >= 1
    assert other_client.status_code == 202


def test_optimizer_post_without_cloudflare_header_uses_peer_bucket(
    settings: Settings, tmp_path: Path
) -> None:
    configured = _custom_settings(
        settings,
        tmp_path,
        optimization_rate_limit_requests=1,
        optimization_rate_limit_window_seconds=60,
        optimization_active_job_limit=10,
    )
    with TestClient(create_app(configured)) as client:
        payload = _optimizer_payload(client)
        first = client.post("/api/v1/optimizations", json=payload)
        repeated = client.post("/api/v1/optimizations", json=payload)

    assert first.status_code == 202
    assert repeated.status_code == 429
    assert int(repeated.headers["Retry-After"]) >= 1


def test_optimizer_post_returns_retry_after_when_active_queue_is_full(
    settings: Settings, tmp_path: Path
) -> None:
    configured = _custom_settings(
        settings,
        tmp_path,
        optimization_rate_limit_requests=12,
        optimization_active_job_limit=1,
    )
    with TestClient(create_app(configured)) as client:
        payload = _optimizer_payload(client)
        first = client.post(
            "/api/v1/optimizations",
            json=payload,
            headers={"CF-Connecting-IP": "203.0.113.1"},
        )
        full = client.post(
            "/api/v1/optimizations",
            json=payload,
            headers={"CF-Connecting-IP": "203.0.113.2"},
        )

    assert first.status_code == 202
    assert full.status_code == 503
    assert int(full.headers["Retry-After"]) >= 1
