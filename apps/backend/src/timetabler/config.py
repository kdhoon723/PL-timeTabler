from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def repository_root() -> Path:
    return Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TIMETABLER_",
        env_file=".env",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = Field(default=1, ge=1, le=32)
    database_url: str = "postgresql+asyncpg://timetabler:timetabler@db:5432/timetabler"
    data_root: Path = Field(default_factory=lambda: repository_root() / "data")
    catalog_validate_checksums: bool = True
    auto_create_schema: bool = False
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    optimization_rate_limit_requests: int = Field(default=12, ge=1, le=1_000)
    optimization_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    optimization_active_job_limit: int = Field(default=100, ge=1, le=100_000)
    optimization_job_retention_hours: int = Field(default=24, ge=1, le=24 * 365)
    auth_enabled: bool = False
    auth_email_domain: str = "daejin.ac.kr"
    auth_email_pattern: str = "{student_number}@{domain}"
    auth_hmac_secret: SecretStr = Field(default_factory=lambda: SecretStr(""))
    auth_email_provider: Literal["disabled", "resend"] = "disabled"
    auth_resend_api_key: SecretStr = Field(default_factory=lambda: SecretStr(""))
    auth_resend_from: str = ""
    auth_rate_limit_window_seconds: int = Field(default=900, ge=60, le=3_600)
    auth_start_account_limit: int = Field(default=5, ge=1, le=100)
    auth_start_ip_limit: int = Field(default=20, ge=1, le=1_000)
    auth_verify_account_limit: int = Field(default=10, ge=1, le=100)
    auth_verify_ip_limit: int = Field(default=50, ge=1, le=1_000)
    auth_session_ttl_seconds: int = Field(default=30 * 24 * 60 * 60, ge=300)
    auth_session_rotation_seconds: int = Field(default=24 * 60 * 60, ge=60)
    auth_otp_record_retention_seconds: int = Field(default=24 * 60 * 60, ge=300)
    auth_session_record_retention_seconds: int = Field(default=7 * 24 * 60 * 60, ge=300)
    auth_session_cookie_name: str = "__Host-timetabler_session"

    def validate_auth_configuration(self, *, external_mailer: bool = False) -> None:
        if not self.auth_enabled:
            return
        secret = self.auth_hmac_secret.get_secret_value()
        if len(secret.encode()) < 32:
            raise ValueError("auth_hmac_secret must contain at least 32 bytes when auth is enabled")
        try:
            address = self.auth_email_pattern.format(
                student_number="20260001",
                domain=self.auth_email_domain,
            )
        except (KeyError, ValueError) as exc:
            raise ValueError("auth_email_pattern contains unsupported placeholders") from exc
        if (
            "\n" in address
            or "\r" in address
            or address.count("@") != 1
            or not address.endswith(f"@{self.auth_email_domain}")
        ):
            raise ValueError("auth_email_pattern must produce an address in auth_email_domain")
        if external_mailer:
            return
        if self.environment == "production" and self.auth_email_provider != "resend":
            raise ValueError("production auth requires the Resend email provider")
        if self.auth_email_provider == "resend" and (
            not self.auth_resend_api_key.get_secret_value() or not self.auth_resend_from
        ):
            raise ValueError("Resend auth requires an API key and from address")


@lru_cache
def get_settings() -> Settings:
    return Settings()
