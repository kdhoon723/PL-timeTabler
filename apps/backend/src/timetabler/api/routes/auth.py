from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from timetabler.api.dependencies import AuthServiceDependency, SettingsDependency
from timetabler.api.rate_limit import client_key_from_headers
from timetabler.api.schemas import (
    AuthSessionRead,
    OtpStartRequest,
    OtpStartResponse,
    OtpVerifyRequest,
)
from timetabler.auth.service import InvalidOtpError

router = APIRouter(prefix="/auth", tags=["auth"])

_START_MESSAGE = "확인 가능한 경우 학교 이메일로 인증 코드를 전송했습니다."
_INVALID_OTP_MESSAGE = "인증 코드가 올바르지 않거나 만료되었습니다."


def _client_ip(request: Request) -> str:
    return client_key_from_headers(
        request.headers.get("CF-Connecting-IP"),
        request.client.host if request.client is not None else None,
    )


def _set_session_cookie(
    response: Response,
    *,
    name: str,
    token: str,
    max_age: int,
) -> None:
    response.set_cookie(
        key=name,
        value=token,
        max_age=max_age,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def _clear_session_cookie(response: Response, name: str) -> None:
    response.delete_cookie(
        key=name,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


@router.post(
    "/otp/start",
    response_model=OtpStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_otp(
    body: OtpStartRequest,
    request: Request,
    auth: AuthServiceDependency,
) -> OtpStartResponse:
    await auth.start_otp(body.student_number, _client_ip(request))
    return OtpStartResponse(message=_START_MESSAGE)


@router.post("/otp/verify", response_model=AuthSessionRead)
async def verify_otp(
    body: OtpVerifyRequest,
    request: Request,
    response: Response,
    auth: AuthServiceDependency,
    settings: SettingsDependency,
) -> AuthSessionRead:
    try:
        created = await auth.verify_otp(
            body.student_number,
            body.code,
            _client_ip(request),
        )
    except InvalidOtpError as exc:
        raise HTTPException(status_code=401, detail=_INVALID_OTP_MESSAGE) from exc
    _set_session_cookie(
        response,
        name=settings.auth_session_cookie_name,
        token=created.token,
        max_age=settings.auth_session_ttl_seconds,
    )
    return AuthSessionRead(
        available=settings.auth_enabled,
        authenticated=True,
        student_number=created.student_number,
        expires_at=created.expires_at,
    )


@router.get("/session", response_model=AuthSessionRead)
async def current_session(
    request: Request,
    response: Response,
    auth: AuthServiceDependency,
    settings: SettingsDependency,
) -> AuthSessionRead:
    token = request.cookies.get(settings.auth_session_cookie_name)
    current = await auth.current_session(token)
    if current is None:
        if token:
            _clear_session_cookie(response, settings.auth_session_cookie_name)
        return AuthSessionRead(available=settings.auth_enabled, authenticated=False)
    if current.rotated_token is not None:
        _set_session_cookie(
            response,
            name=settings.auth_session_cookie_name,
            token=current.rotated_token,
            max_age=settings.auth_session_ttl_seconds,
        )
    return AuthSessionRead(
        available=settings.auth_enabled,
        authenticated=True,
        student_number=current.student_number,
        expires_at=current.expires_at,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    auth: AuthServiceDependency,
    settings: SettingsDependency,
) -> None:
    await auth.logout(request.cookies.get(settings.auth_session_cookie_name))
    _clear_session_cookie(response, settings.auth_session_cookie_name)
