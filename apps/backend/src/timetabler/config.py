from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
