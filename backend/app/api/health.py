from fastapi import APIRouter

from app import __version__
from app.api.deps import AppContainer
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(container: AppContainer) -> HealthResponse:
    settings = container.settings
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        environment=settings.environment,
        agent_provider=container.agent.provider_name,
        agent_model=container.agent.provider_model,
        demo_mode=container.agent.provider_name == "mock",
    )
