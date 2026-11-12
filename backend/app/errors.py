"""Domain errors shared by services, tools, and API routes."""


class DomainError(Exception):
    code = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class InvalidInputError(DomainError):
    code = "invalid_arguments"


class ProviderUnavailableError(DomainError):
    """The configured model provider can't serve the request (credentials, quota, network)."""

    code = "provider_unavailable"
