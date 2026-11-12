"""Tool definitions shared by all agent tools."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from app.repositories.base import ContentRepository

if TYPE_CHECKING:
    from app.services.proposals import ProposalService


class ToolKind(StrEnum):
    READ = "read"  # no side effects
    PROPOSE = "propose"  # creates a *pending* proposal; never modifies content


class ToolInput(BaseModel):
    """Base for tool arguments: unknown keys are rejected, strings are stripped."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, frozen=True)


@dataclass(frozen=True)
class ToolContext:
    content_repo: ContentRepository
    proposals: "ProposalService"
    as_of: date  # "today" for staleness checks; fixed in demo mode for reproducible results
    site_base_url: str


@dataclass(frozen=True)
class Tool[InT: ToolInput, OutT: BaseModel]:
    name: str
    description: str
    kind: ToolKind
    input_model: type[InT]
    output_model: type[OutT]
    handler: Callable[[ToolContext, InT], OutT]

    def json_schema(self) -> dict[str, Any]:
        return self.input_model.model_json_schema()


class ToolStatus(StrEnum):
    OK = "ok"
    UNKNOWN_TOOL = "unknown_tool"
    INVALID_ARGUMENTS = "invalid_arguments"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    TIMEOUT = "timeout"
    OUTPUT_TOO_LARGE = "output_too_large"
    ERROR = "error"


class ToolExecution(BaseModel):
    """Envelope returned for every tool call, success or failure."""

    tool_name: str
    status: ToolStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int

    @property
    def ok(self) -> bool:
        return self.status is ToolStatus.OK
