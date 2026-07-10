from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from timetabler.api.app import create_app
from timetabler.auth.mailer import DisabledOtpMailer
from timetabler.auth.service import AuthService, InvalidOtpError
from timetabler.config import Settings, repository_root
from timetabler.db.models import AuthOtpChallenge, AuthSession
from timetabler.db.session import Database


@dataclass(slots=True)
class FakeMailer:
    deliveries: list[tuple[str, str, str]] = field(default_factory=list)

    async def send_otp(self, recipient: str, code: str, *, challenge_id: str) -> None:
        self.deliveries.append((recipient, code, challenge_id))


def auth_settings(tmp_path: Path, **updates: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "database_url": f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}",
        "data_root": repository_root() / "data",
        "catalog_validate_checksums": True,
        "auto_create_schema": True,
        "cors_origins": ["https://testserver"],
        "auth_enabled": True,
        "auth_hmac_secret": "test-secret-that-is-at-least-32-bytes-long",
        "auth_email_provider": "disabled",
    }
    values.update(updates)
    return Settings(**values)


async def create_auth_service(
    settings: Settings,
    mailer: FakeMailer | DisabledOtpMailer,
) -> tuple[Database, AuthService]:
    database = Database(settings.database_url)
    await database.create_schema()
    return database, AuthService(database.session_factory, settings, mailer)


def wrong_code_for(code: str) -> str:
    return "999999" if code != "999999" else "888888"


async def test_otp_is_secure_random_shape_and_only_digest_is_stored(tmp_path: Path) -> None:
    settings = auth_settings(tmp_path)
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)

    await service.start_otp("20260001", "203.0.113.10")

    assert len(mailer.deliveries) == 1
    recipient, code, challenge_id = mailer.deliveries[0]
    assert recipient == "20260001@daejin.ac.kr"
    assert len(code) == 6 and code.isdigit()
    async with database.session_factory() as session:
        challenge = await session.get(AuthOtpChallenge, challenge_id)
        assert challenge is not None
        assert challenge.code_digest != code
        assert code not in challenge.code_digest
        assert len(challenge.code_digest) == 64
        assert (
            challenge.expires_at.replace(tzinfo=UTC) - challenge.last_sent_at.replace(tzinfo=UTC)
        ) == timedelta(minutes=5)
    await database.close()


async def test_otp_is_one_time_and_session_token_is_hashed(tmp_path: Path) -> None:
    settings = auth_settings(tmp_path)
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)
    await service.start_otp("20260002", "203.0.113.11")
    code = mailer.deliveries[0][1]

    created = await service.verify_otp("20260002", code, "203.0.113.11")

    assert created.student_number == "20260002"
    async with database.session_factory() as session:
        stored = (await session.scalars(select(AuthSession))).one()
        challenge = (await session.scalars(select(AuthOtpChallenge))).one()
        assert stored.token_digest != created.token
        assert created.token not in stored.token_digest
        assert len(stored.token_digest) == 64
        assert challenge.consumed_at is not None
    with pytest.raises(InvalidOtpError):
        await service.verify_otp("20260002", code, "203.0.113.11")
    await database.close()


async def test_expiry_and_five_failed_attempts_invalidate_challenges(tmp_path: Path) -> None:
    settings = auth_settings(tmp_path, auth_verify_account_limit=20)
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)
    await service.start_otp("20260003", "203.0.113.12")
    first_code, first_id = mailer.deliveries[0][1:]
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthOtpChallenge)
            .where(AuthOtpChallenge.id == first_id)
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    with pytest.raises(InvalidOtpError):
        await service.verify_otp("20260003", first_code, "203.0.113.12")

    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthOtpChallenge)
            .where(AuthOtpChallenge.id == first_id)
            .values(last_sent_at=datetime.now(UTC) - timedelta(seconds=61))
        )
    await service.start_otp("20260003", "203.0.113.12")
    second_code, second_id = mailer.deliveries[1][1:]
    for _ in range(5):
        with pytest.raises(InvalidOtpError):
            await service.verify_otp(
                "20260003",
                wrong_code_for(second_code),
                "203.0.113.12",
            )
    with pytest.raises(InvalidOtpError):
        await service.verify_otp("20260003", second_code, "203.0.113.12")
    async with database.session_factory() as session:
        second = await session.get(AuthOtpChallenge, second_id)
        assert second is not None
        assert second.attempts == 5
        assert second.invalidated_at is not None
    await database.close()


async def test_resend_cooldown_and_new_code_invalidate_previous_code(tmp_path: Path) -> None:
    settings = auth_settings(tmp_path)
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)
    await service.start_otp("20260004", "203.0.113.13")
    first_code, first_id = mailer.deliveries[0][1:]

    await service.start_otp("20260004", "203.0.113.13")
    assert len(mailer.deliveries) == 1

    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthOtpChallenge)
            .where(AuthOtpChallenge.id == first_id)
            .values(last_sent_at=datetime.now(UTC) - timedelta(seconds=61))
        )
    await service.start_otp("20260004", "203.0.113.13")
    assert len(mailer.deliveries) == 2
    second_code = mailer.deliveries[1][1]

    with pytest.raises(InvalidOtpError):
        await service.verify_otp("20260004", first_code, "203.0.113.13")
    created = await service.verify_otp("20260004", second_code, "203.0.113.13")
    assert created.student_number == "20260004"
    async with database.session_factory() as session:
        first = await session.get(AuthOtpChallenge, first_id)
        assert first is not None and first.invalidated_at is not None
    await database.close()


async def test_cooldown_requests_do_not_consume_send_quota(tmp_path: Path) -> None:
    settings = auth_settings(
        tmp_path,
        auth_start_account_limit=2,
        auth_start_ip_limit=20,
    )
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)
    await service.start_otp("20260014", "203.0.113.24")
    first_id = mailer.deliveries[0][2]

    for _ in range(8):
        await service.start_otp("20260014", "203.0.113.24")
    assert len(mailer.deliveries) == 1

    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthOtpChallenge)
            .where(AuthOtpChallenge.id == first_id)
            .values(last_sent_at=datetime.now(UTC) - timedelta(seconds=61))
        )
    await service.start_otp("20260014", "203.0.113.24")
    assert len(mailer.deliveries) == 2
    await database.close()


async def test_account_and_ip_start_throttles_do_not_send_extra_mail(tmp_path: Path) -> None:
    settings = auth_settings(
        tmp_path,
        auth_start_account_limit=2,
        auth_start_ip_limit=2,
    )
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)

    await service.start_otp("20260005", "203.0.113.14")
    first_id = mailer.deliveries[-1][2]
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthOtpChallenge)
            .where(AuthOtpChallenge.id == first_id)
            .values(last_sent_at=datetime.now(UTC) - timedelta(seconds=61))
        )
    await service.start_otp("20260005", "203.0.113.14")
    second_id = mailer.deliveries[-1][2]
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthOtpChallenge)
            .where(AuthOtpChallenge.id == second_id)
            .values(last_sent_at=datetime.now(UTC) - timedelta(seconds=61))
        )
    await service.start_otp("20260005", "198.51.100.1")
    assert len(mailer.deliveries) == 2  # account limit

    await service.start_otp("20260006", "203.0.113.14")
    assert len(mailer.deliveries) == 2  # original IP already reached its limit
    await database.close()


async def test_verify_throttle_is_generic_across_accounts_for_one_ip(tmp_path: Path) -> None:
    settings = auth_settings(
        tmp_path,
        auth_verify_account_limit=10,
        auth_verify_ip_limit=1,
    )
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)
    await service.start_otp("20260010", "203.0.113.20")
    await service.start_otp("20260011", "203.0.113.21")

    with pytest.raises(InvalidOtpError):
        await service.verify_otp(
            "20260010",
            wrong_code_for(mailer.deliveries[0][1]),
            "198.51.100.20",
        )
    with pytest.raises(InvalidOtpError):
        await service.verify_otp(
            "20260011",
            mailer.deliveries[1][1],
            "198.51.100.20",
        )
    await database.close()


async def test_session_rotation_expiration_and_logout(tmp_path: Path) -> None:
    settings = auth_settings(tmp_path, auth_session_rotation_seconds=60)
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)
    await service.start_otp("20260007", "203.0.113.15")
    created = await service.verify_otp(
        "20260007",
        mailer.deliveries[0][1],
        "203.0.113.15",
    )
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthSession).values(rotated_at=datetime.now(UTC) - timedelta(seconds=61))
        )

    current = await service.current_session(created.token)
    assert current is not None and current.rotated_token is not None
    assert await service.current_session(created.token) is None
    assert await service.current_session(current.rotated_token) is not None

    await service.logout(current.rotated_token)
    assert await service.current_session(current.rotated_token) is None

    await service.start_otp("20260012", "203.0.113.15")
    expiring = await service.verify_otp(
        "20260012",
        mailer.deliveries[-1][1],
        "203.0.113.15",
    )
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthSession)
            .where(AuthSession.student_number == "20260012")
            .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        )
    assert await service.current_session(expiring.token) is None
    await database.close()


async def test_expired_auth_records_are_purged_on_auth_requests(tmp_path: Path) -> None:
    settings = auth_settings(
        tmp_path,
        auth_otp_record_retention_seconds=300,
        auth_session_record_retention_seconds=300,
    )
    mailer = FakeMailer()
    database, service = await create_auth_service(settings, mailer)
    await service.start_otp("20260015", "203.0.113.25")
    challenge_id = mailer.deliveries[0][2]
    created = await service.verify_otp(
        "20260015",
        mailer.deliveries[0][1],
        "203.0.113.25",
    )
    old = datetime.now(UTC) - timedelta(seconds=301)
    async with database.session_factory() as session, session.begin():
        await session.execute(
            update(AuthOtpChallenge)
            .where(AuthOtpChallenge.id == challenge_id)
            .values(created_at=old)
        )
        await session.execute(
            update(AuthSession)
            .where(AuthSession.student_number == created.student_number)
            .values(revoked_at=old)
        )

    await service.start_otp("20260016", "203.0.113.26")
    async with database.session_factory() as session:
        assert await session.get(AuthOtpChallenge, challenge_id) is None
        assert (
            await session.scalars(
                select(AuthSession).where(AuthSession.student_number == created.student_number)
            )
        ).one_or_none() is None
    await database.close()


async def test_disabled_development_mailer_invalidates_undelivered_code(tmp_path: Path) -> None:
    settings = auth_settings(tmp_path)
    database, service = await create_auth_service(settings, DisabledOtpMailer())

    await service.start_otp("20260008", "203.0.113.16")

    async with database.session_factory() as session:
        challenge = (await session.scalars(select(AuthOtpChallenge))).one()
        assert challenge.invalidated_at is not None
    await database.close()


def test_auth_api_uses_generic_responses_and_secure_cookie(tmp_path: Path) -> None:
    settings = auth_settings(tmp_path, auth_start_account_limit=1)
    mailer = FakeMailer()
    with TestClient(
        create_app(settings, otp_mailer=mailer),
        base_url="https://testserver",
    ) as client:
        first = client.post("/api/v1/auth/otp/start", json={"studentNumber": "20260009"})
        throttled = client.post(
            "/api/v1/auth/otp/start",
            json={"studentNumber": "20260009"},
        )
        assert first.status_code == throttled.status_code == 202
        assert first.json() == throttled.json()
        assert "20260009" not in first.text
        assert "daejin.ac.kr" not in first.text
        assert len(mailer.deliveries) == 1

        wrong = client.post(
            "/api/v1/auth/otp/verify",
            json={"studentNumber": "20260009", "code": wrong_code_for(mailer.deliveries[0][1])},
        )
        unknown = client.post(
            "/api/v1/auth/otp/verify",
            json={"studentNumber": "20999999", "code": "123456"},
        )
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()

        verified = client.post(
            "/api/v1/auth/otp/verify",
            json={"studentNumber": "20260009", "code": mailer.deliveries[0][1]},
        )
        assert verified.status_code == 200
        assert verified.json()["authenticated"] is True
        assert "token" not in verified.text.casefold()
        cookie = verified.headers["set-cookie"].casefold()
        assert "secure" in cookie
        assert "httponly" in cookie
        assert "samesite=lax" in cookie

        current = client.get("/api/v1/auth/session")
        assert current.status_code == 200
        assert current.json()["studentNumber"] == "20260009"
        assert current.headers["cache-control"] == "no-store, private"
        assert current.headers["pragma"] == "no-cache"
        assert current.headers["vary"] == "Cookie"
        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 204
        assert client.get("/api/v1/auth/session").json() == {
            "available": True,
            "authenticated": False,
            "studentNumber": None,
            "expiresAt": None,
        }


def test_auth_input_contract_rejects_non_student_numbers_and_non_six_digit_codes(
    tmp_path: Path,
) -> None:
    settings = auth_settings(tmp_path)
    with TestClient(
        create_app(settings, otp_mailer=FakeMailer()),
        base_url="https://testserver",
    ) as client:
        assert (
            client.post(
                "/api/v1/auth/otp/start", json={"studentNumber": "user@example.com"}
            ).status_code
            == 422
        )
        assert (
            client.post(
                "/api/v1/auth/otp/verify",
                json={"studentNumber": "20260001", "code": "12345"},
            ).status_code
            == 422
        )


def test_production_auth_requires_secret_and_real_provider(tmp_path: Path) -> None:
    missing_secret = auth_settings(
        tmp_path,
        environment="production",
        auth_hmac_secret="short",
        auth_email_provider="resend",
        auth_resend_api_key="key",
        auth_resend_from="PL-timeTabler <auth@example.com>",
    )
    with pytest.raises(ValueError, match="32 bytes"):
        missing_secret.validate_auth_configuration()

    disabled_provider = auth_settings(tmp_path, environment="production")
    with pytest.raises(ValueError, match="Resend"):
        disabled_provider.validate_auth_configuration()
