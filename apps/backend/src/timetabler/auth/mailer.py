from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from timetabler.config import Settings


class MailDeliveryError(RuntimeError):
    pass


class OtpMailer(Protocol):
    async def send_otp(self, recipient: str, code: str, *, challenge_id: str) -> None: ...


class DisabledOtpMailer:
    """Safe local default: never sends or exposes an authentication code."""

    async def send_otp(self, recipient: str, code: str, *, challenge_id: str) -> None:
        del recipient, code, challenge_id
        raise MailDeliveryError("email delivery is disabled")


@dataclass(frozen=True, slots=True)
class ResendOtpMailer:
    api_key: str
    from_address: str
    timeout_seconds: float = 10

    async def send_otp(self, recipient: str, code: str, *, challenge_id: str) -> None:
        await asyncio.to_thread(self._send, recipient, code, challenge_id)

    def _send(self, recipient: str, code: str, challenge_id: str) -> None:
        payload = json.dumps(
            {
                "from": self.from_address,
                "to": [recipient],
                "subject": "PL-timeTabler 대진대학교 이메일 인증",
                "text": (
                    f"인증 코드는 {code}입니다. "
                    "이 코드는 5분 동안 유효하며 다른 사람에게 공유하면 안 됩니다."
                ),
            },
            ensure_ascii=False,
        ).encode()
        request = Request(
            "https://api.resend.com/emails",
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": f"timetabler-otp-{challenge_id}",
                "User-Agent": "PL-timeTabler/1.0",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                if not 200 <= response.status < 300:
                    raise MailDeliveryError("email provider rejected the request")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise MailDeliveryError("email provider request failed") from exc


def build_otp_mailer(settings: Settings) -> OtpMailer:
    if settings.auth_email_provider == "resend":
        return ResendOtpMailer(
            api_key=settings.auth_resend_api_key.get_secret_value(),
            from_address=settings.auth_resend_from,
        )
    return DisabledOtpMailer()
