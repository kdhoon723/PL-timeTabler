from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from timetabler.auth.mailer import OtpMailer
from timetabler.config import Settings
from timetabler.db.models import AuthOtpChallenge, AuthRateEvent, AuthSession


class InvalidOtpError(RuntimeError):
    pass


OTP_EXPIRY = timedelta(minutes=5)
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN = timedelta(seconds=60)


@dataclass(frozen=True, slots=True)
class CreatedSession:
    student_number: str
    token: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class CurrentSession:
    student_number: str
    expires_at: datetime
    rotated_token: str | None = None


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        mailer: OtpMailer,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._mailer = mailer
        configured_secret = settings.auth_hmac_secret.get_secret_value()
        self._secret = configured_secret.encode() if configured_secret else secrets.token_bytes(32)

    async def start_otp(self, student_number: str, client_ip: str) -> None:
        if not self._settings.auth_enabled:
            return
        now = datetime.now(UTC)
        account_digest = self._digest("account", student_number)
        ip_digest = self._digest("ip", client_ip)
        challenge_id: str | None = None
        code: str | None = None
        recipient: str | None = None

        async with self._session_factory() as session, session.begin():
            await self._advisory_locks(session, account_digest, ip_digest)
            await self._purge_expired_records(session, now)
            latest = (
                await session.scalars(
                    select(AuthOtpChallenge)
                    .where(AuthOtpChallenge.student_number == student_number)
                    .order_by(AuthOtpChallenge.created_at.desc(), AuthOtpChallenge.id.desc())
                    .limit(1)
                    .with_for_update()
                )
            ).one_or_none()
            if latest is not None and now - _utc(latest.last_sent_at) < OTP_RESEND_COOLDOWN:
                return
            allowed = await self._admit_rate_event(
                session,
                kind="OTP_START",
                account_digest=account_digest,
                ip_digest=ip_digest,
                account_limit=self._settings.auth_start_account_limit,
                ip_limit=self._settings.auth_start_ip_limit,
                now=now,
            )
            if not allowed:
                return

            await session.execute(
                update(AuthOtpChallenge)
                .where(
                    AuthOtpChallenge.student_number == student_number,
                    AuthOtpChallenge.consumed_at.is_(None),
                    AuthOtpChallenge.invalidated_at.is_(None),
                )
                .values(invalidated_at=now)
            )
            challenge_id = str(uuid4())
            code = f"{secrets.randbelow(1_000_000):06d}"
            recipient = self._derive_email(student_number)
            session.add(
                AuthOtpChallenge(
                    id=challenge_id,
                    student_number=student_number,
                    code_digest=self._otp_digest(challenge_id, code),
                    attempts=0,
                    expires_at=now + OTP_EXPIRY,
                    last_sent_at=now,
                    consumed_at=None,
                    invalidated_at=None,
                    created_at=now,
                )
            )

        if challenge_id is None or code is None or recipient is None:
            return
        try:
            await self._mailer.send_otp(recipient, code, challenge_id=challenge_id)
        except Exception:
            # The public response remains generic. Invalidate the undelivered
            # challenge without ever logging or returning its plaintext code.
            async with self._session_factory() as session, session.begin():
                await session.execute(
                    update(AuthOtpChallenge)
                    .where(
                        AuthOtpChallenge.id == challenge_id,
                        AuthOtpChallenge.consumed_at.is_(None),
                    )
                    .values(invalidated_at=datetime.now(UTC))
                )

    async def verify_otp(
        self,
        student_number: str,
        code: str,
        client_ip: str,
    ) -> CreatedSession:
        if not self._settings.auth_enabled:
            raise InvalidOtpError
        now = datetime.now(UTC)
        account_digest = self._digest("account", student_number)
        ip_digest = self._digest("ip", client_ip)
        created: CreatedSession | None = None

        async with self._session_factory() as session, session.begin():
            await self._advisory_locks(session, account_digest, ip_digest)
            await self._purge_expired_records(session, now)
            allowed = await self._admit_rate_event(
                session,
                kind="OTP_VERIFY",
                account_digest=account_digest,
                ip_digest=ip_digest,
                account_limit=self._settings.auth_verify_account_limit,
                ip_limit=self._settings.auth_verify_ip_limit,
                now=now,
            )
            challenge = None
            if allowed:
                challenge = (
                    await session.scalars(
                        select(AuthOtpChallenge)
                        .where(
                            AuthOtpChallenge.student_number == student_number,
                            AuthOtpChallenge.consumed_at.is_(None),
                            AuthOtpChallenge.invalidated_at.is_(None),
                        )
                        .order_by(AuthOtpChallenge.created_at.desc(), AuthOtpChallenge.id.desc())
                        .limit(1)
                        .with_for_update()
                    )
                ).one_or_none()

            if challenge is not None:
                if _utc(challenge.expires_at) <= now or challenge.attempts >= OTP_MAX_ATTEMPTS:
                    challenge.invalidated_at = now
                elif not hmac.compare_digest(
                    challenge.code_digest,
                    self._otp_digest(challenge.id, code),
                ):
                    challenge.attempts += 1
                    if challenge.attempts >= OTP_MAX_ATTEMPTS:
                        challenge.invalidated_at = now
                else:
                    challenge.consumed_at = now
                    token = secrets.token_urlsafe(32)
                    expires_at = now + timedelta(seconds=self._settings.auth_session_ttl_seconds)
                    await session.execute(
                        update(AuthSession)
                        .where(
                            AuthSession.student_number == student_number,
                            AuthSession.revoked_at.is_(None),
                        )
                        .values(revoked_at=now)
                    )
                    session.add(
                        AuthSession(
                            id=str(uuid4()),
                            student_number=student_number,
                            token_digest=self._session_digest(token),
                            expires_at=expires_at,
                            revoked_at=None,
                            rotated_at=now,
                            created_at=now,
                        )
                    )
                    created = CreatedSession(student_number, token, expires_at)

        if created is None:
            raise InvalidOtpError
        return created

    async def current_session(self, token: str | None) -> CurrentSession | None:
        if not self._settings.auth_enabled or not token:
            return None
        now = datetime.now(UTC)
        token_digest = self._session_digest(token)
        current: CurrentSession | None = None
        async with self._session_factory() as session, session.begin():
            await self._purge_expired_records(session, now)
            auth_session = (
                await session.scalars(
                    select(AuthSession)
                    .where(AuthSession.token_digest == token_digest)
                    .limit(1)
                    .with_for_update()
                )
            ).one_or_none()
            if auth_session is not None and auth_session.revoked_at is None:
                if _utc(auth_session.expires_at) <= now:
                    auth_session.revoked_at = now
                else:
                    rotated_token: str | None = None
                    if _utc(auth_session.rotated_at) <= now - timedelta(
                        seconds=self._settings.auth_session_rotation_seconds
                    ):
                        rotated_token = secrets.token_urlsafe(32)
                        auth_session.token_digest = self._session_digest(rotated_token)
                        auth_session.rotated_at = now
                    current = CurrentSession(
                        student_number=auth_session.student_number,
                        expires_at=_utc(auth_session.expires_at),
                        rotated_token=rotated_token,
                    )
        return current

    async def logout(self, token: str | None) -> None:
        if not token:
            return
        now = datetime.now(UTC)
        async with self._session_factory() as session, session.begin():
            await self._purge_expired_records(session, now)
            await session.execute(
                update(AuthSession)
                .where(
                    AuthSession.token_digest == self._session_digest(token),
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )

    def _derive_email(self, student_number: str) -> str:
        return self._settings.auth_email_pattern.format(
            student_number=student_number,
            domain=self._settings.auth_email_domain,
        )

    def _digest(self, purpose: str, value: str) -> str:
        return hmac.new(
            self._secret,
            f"{purpose}\0{value}".encode(),
            hashlib.sha256,
        ).hexdigest()

    def _otp_digest(self, challenge_id: str, code: str) -> str:
        return self._digest("otp", f"{challenge_id}\0{code}")

    def _session_digest(self, token: str) -> str:
        return self._digest("session", token)

    async def _purge_expired_records(self, session: AsyncSession, now: datetime) -> None:
        otp_cutoff = now - timedelta(seconds=self._settings.auth_otp_record_retention_seconds)
        session_cutoff = now - timedelta(
            seconds=self._settings.auth_session_record_retention_seconds
        )
        await session.execute(
            delete(AuthOtpChallenge).where(AuthOtpChallenge.created_at < otp_cutoff)
        )
        await session.execute(
            delete(AuthSession).where(
                or_(
                    AuthSession.expires_at < session_cutoff,
                    AuthSession.revoked_at < session_cutoff,
                )
            )
        )

    async def _admit_rate_event(
        self,
        session: AsyncSession,
        *,
        kind: str,
        account_digest: str,
        ip_digest: str,
        account_limit: int,
        ip_limit: int,
        now: datetime,
    ) -> bool:
        cutoff = now - timedelta(seconds=self._settings.auth_rate_limit_window_seconds)
        await session.execute(delete(AuthRateEvent).where(AuthRateEvent.created_at < cutoff))
        account_count = int(
            await session.scalar(
                select(func.count())
                .select_from(AuthRateEvent)
                .where(
                    AuthRateEvent.kind == kind,
                    AuthRateEvent.account_digest == account_digest,
                    AuthRateEvent.created_at >= cutoff,
                )
            )
            or 0
        )
        ip_count = int(
            await session.scalar(
                select(func.count())
                .select_from(AuthRateEvent)
                .where(
                    AuthRateEvent.kind == kind,
                    AuthRateEvent.ip_digest == ip_digest,
                    AuthRateEvent.created_at >= cutoff,
                )
            )
            or 0
        )
        if account_count >= account_limit or ip_count >= ip_limit:
            return False
        session.add(
            AuthRateEvent(
                id=str(uuid4()),
                kind=kind,
                account_digest=account_digest,
                ip_digest=ip_digest,
                created_at=now,
            )
        )
        return True

    @staticmethod
    async def _advisory_locks(session: AsyncSession, *digests: str) -> None:
        if session.get_bind().dialect.name != "postgresql":
            return
        lock_ids = sorted({int(digest[:16], 16) & ((1 << 63) - 1) for digest in digests})
        for lock_id in lock_ids:
            await session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_id)"),
                {"lock_id": lock_id},
            )
