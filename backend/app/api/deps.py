from typing import Annotated, cast

from fastapi import Depends, Request

from app.config import Settings
from app.repositories.base import ContentRepository


def get_app_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_content_repository(request: Request) -> ContentRepository:
    return cast(ContentRepository, request.app.state.content_repo)


AppSettings = Annotated[Settings, Depends(get_app_settings)]
ContentRepo = Annotated[ContentRepository, Depends(get_content_repository)]
