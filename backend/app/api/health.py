from fastapi import APIRouter

from app import __version__
from app.api.deps import AppSettings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(settings: AppSettings) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        environment=settings.environment,
        agent_provider=settings.agent_provider,
    )
