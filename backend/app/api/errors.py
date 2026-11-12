from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import (
    ConflictError,
    DomainError,
    InvalidInputError,
    NotFoundError,
    ProviderUnavailableError,
)

_STATUS: dict[type[DomainError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    InvalidInputError: 422,
    ProviderUnavailableError: 503,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=_STATUS.get(type(exc), 400),
            content={"detail": exc.message, "code": exc.code},
        )
