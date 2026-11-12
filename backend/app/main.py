import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.content import router as content_router
from app.api.health import router as health_router
from app.config import Settings, get_settings
from app.repositories.sqlite import SQLiteContentRepository
from app.services.seeding import ensure_seeded

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    repo = SQLiteContentRepository(settings.database_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        inserted = ensure_seeded(repo)
        if inserted:
            logger.info("Seeded %d content entries into %s", inserted, settings.database_path)
        yield

    app = FastAPI(title=settings.app_name, version=__version__, lifespan=lifespan)
    app.state.settings = settings
    app.state.content_repo = repo

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(content_router, prefix="/api")
    return app


app = create_app()
