"""Application settings loaded from environment variables (see ../.env.example)."""

from functools import lru_cache
from typing import Literal

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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
