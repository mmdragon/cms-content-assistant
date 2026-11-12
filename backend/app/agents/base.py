"""Provider-independent agent contracts.

A provider (the deterministic mock today, optionally a model-backed one later) receives the
conversation and a ToolRunner. It can only touch data through the runner, which goes through
the allowlisted ToolRegistry and enforces a per-turn tool-call budget.
"""

from collections.abc import Mapping
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.proposal import EditableField
from app.tools.base import ToolContext, ToolExecution, ToolStatus
from app.tools.findings import Finding
from app.tools.registry import ToolRegistry

MAX_MESSAGES = 20
MAX_MESSAGE_CHARS = 2000
DEFAULT_MAX_TOOL_CALLS = 25


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(min_length=1, max_length=MAX_MESSAGE_CHARS)]


class ChatRequest(BaseModel):
    """The conversation so far (oldest first). The last message must be from the user."""

    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)

    @model_validator(mode="after")
    def _last_is_user(self) -> "ChatRequest":
        if self.messages[-1].role != "user":
            raise ValueError("the last message must have role 'user'")
        if not self.messages[-1].content.strip():
            raise ValueError("the last message must not be blank")
        return self

    @property
    def latest(self) -> str:
        return self.messages[-1].content.strip()


class ToolCallRecord(BaseModel):
    tool_name: str
    arguments: dict[str, Any]
    status: ToolStatus
    duration_ms: int
    error: str | None = None


class ProposalRef(BaseModel):
    proposal_id: str
    content_id: str
    title: str
    field_name: EditableField


class AgentResponse(BaseModel):
    provider: str
    demo_mode: bool
    intents: list[str]
    message: str
    findings: list[Finding] = Field(default_factory=list)
    proposals: list[ProposalRef] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ToolBudgetExceeded(Exception):
    pass


class ToolRunner:
    """Executes allowlisted tools for one agent turn and records every call."""

    def __init__(
        self, registry: ToolRegistry, ctx: ToolContext, max_calls: int = DEFAULT_MAX_TOOL_CALLS
    ) -> None:
        self._registry = registry
        self._ctx = ctx
        self._max_calls = max_calls
        self.calls: list[ToolCallRecord] = []

    @property
    def remaining(self) -> int:
        return self._max_calls - len(self.calls)

    def run(self, name: str, arguments: Mapping[str, Any] | None = None) -> ToolExecution:
        if self.remaining <= 0:
            raise ToolBudgetExceeded(f"tool-call limit of {self._max_calls} reached")
        args = dict(arguments or {})
        execution = self._registry.execute(name, args, self._ctx)
        self.calls.append(
            ToolCallRecord(
                tool_name=name,
                arguments=args,
                status=execution.status,
                duration_ms=execution.duration_ms,
                error=execution.error,
            )
        )
        return execution


class AgentProvider(Protocol):
    name: str
    demo_mode: bool

    def respond(self, request: ChatRequest, tools: ToolRunner) -> AgentResponse: ...
