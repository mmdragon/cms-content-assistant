from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repositories.sqlite import SQLiteContentRepository
from app.services.seeding import seed_repository


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(environment="test", database_path=str(tmp_path / "test.db"))


@pytest.fixture
def repo(tmp_path: Path) -> SQLiteContentRepository:
    repository = SQLiteContentRepository(tmp_path / "repo.db")
    seed_repository(repository)
    return repository


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    # Using the client as a context manager runs the lifespan, which seeds the DB.
    with TestClient(create_app(settings)) as test_client:
        yield test_client
