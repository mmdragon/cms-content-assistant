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
    # "mock": deterministic demo agent, no API key, no cost (default).
    # "claude": Claude via the Anthropic API. Needs ANTHROPIC_API_KEY (read by the SDK from the
    # environment, never stored here) and is billed per token to that API account.
    agent_provider: Literal["mock", "claude"] = "mock"
    claude_model: str = "claude-opus-5-5"
    claude_effort: Literal["low", "medium", "high", "xhigh", "max"] = "medium"
    claude_max_iterations: int = Field(default=8, ge=1, le=20)
    claude_max_tokens: int = Field(default=16_000, ge=1_000, le=32_000)
    claude_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    claude_fallbacks: bool = True
    # The site's public origin; absolute links on this domain count as internal links.
    site_base_url: str = "https://www.northstarliving.example"
    # "Today" for staleness audits. Pin it (e.g. 2026-11-12) so demo results never drift;
    # leave unset to use the real current date.
    audit_reference_date: date | None = None
    tool_timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    # Upper bound on tool calls in a single assistant turn.
    agent_max_tool_calls: int = Field(default=25, ge=1, le=100)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def audit_as_of(self) -> date:
        return self.audit_reference_date or datetime.now(UTC).date()


@lru_cache
def get_settings() -> Settings:
    return Settings()
