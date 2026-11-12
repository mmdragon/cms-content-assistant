import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.activity import router as activity_router
from app.api.content import router as content_router
from app.api.errors import register_error_handlers
from app.api.health import router as health_router
from app.api.proposals import router as proposals_router
from app.config import Settings, get_settings
from app.container import build_container
from app.services.audit import Clock, utc_now
from app.services.seeding import ensure_seeded

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, clock: Clock = utc_now) -> FastAPI:
    settings = settings or get_settings()
    container = build_container(settings, clock)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        inserted = ensure_seeded(container.content_repo)
        if inserted:
            logger.info("Seeded %d content entries into %s", inserted, settings.database_path)
        yield

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.container = container

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    register_error_handlers(app)

    for router in (health_router, content_router, proposals_router, activity_router):
        app.include_router(router, prefix="/api")
    return app


app = create_app()
