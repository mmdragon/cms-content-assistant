from typing import Annotated, cast

from fastapi import Depends, Request

from app.config import Settings
from app.container import Container
from app.repositories.base import ContentRepository


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


def get_app_settings(container: Annotated[Container, Depends(get_container)]) -> Settings:
    return container.settings


def get_content_repository(
    container: Annotated[Container, Depends(get_container)],
) -> ContentRepository:
    return container.content_repo


AppContainer = Annotated[Container, Depends(get_container)]
AppSettings = Annotated[Settings, Depends(get_app_settings)]
ContentRepo = Annotated[ContentRepository, Depends(get_content_repository)]
