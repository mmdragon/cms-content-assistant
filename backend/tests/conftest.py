from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.container import Container
from app.main import create_app
from app.repositories.sqlite import SQLiteContentRepository
from app.services.seeding import seed_repository
from app.tools.base import ToolContext, ToolExecution
from tests.seed_manifest import SEED_REFERENCE_DATE


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_path=str(tmp_path / "test.db"),
        audit_reference_date=SEED_REFERENCE_DATE.date(),
    )


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


@pytest.fixture
def container(client: TestClient) -> Container:
    """The same container (and database) the API client uses."""
    return cast(Container, client.app.state.container)  # type: ignore[attr-defined]


@pytest.fixture
def ctx(container: Container) -> ToolContext:
    return container.tool_context()


RunTool = Callable[..., ToolExecution]


@pytest.fixture
def run_tool(container: Container, ctx: ToolContext) -> RunTool:
    def _run(name: str, arguments: Any = None) -> ToolExecution:
        return container.tools.execute(name, arguments, ctx)

    return _run
