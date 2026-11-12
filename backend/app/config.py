"""Application settings loaded from environment variables (see ../.env.example)."""

from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CMS_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CMS Content Assistant"
    environment: Literal["development", "test", "production"] = "development"
    database_path: str = "data/cms.db"
    # Comma-separated list of origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    # "mock" works with no API key. A real provider is added in a later phase.
    agent_provider: Literal["mock"] = "mock"
    # The site's public origin; absolute links on this domain count as internal links.
    site_base_url: str = "https://www.northstarliving.example"
    # "Today" for staleness audits. Pin it (e.g. 2026-11-12) so demo results never drift;
    # leave unset to use the real current date.
    audit_reference_date: date | None = None
    tool_timeout_seconds: float = Field(default=5.0, gt=0, le=60)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def audit_as_of(self) -> date:
        return self.audit_reference_date or datetime.now(UTC).date()


@lru_cache
def get_settings() -> Settings:
    return Settings()
