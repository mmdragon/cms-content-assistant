from typing import Annotated

from fastapi import APIRouter, Depends

from app import __version__
from app.config import Settings, get_settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        environment=settings.environment,
        agent_provider=settings.agent_provider,
    )
