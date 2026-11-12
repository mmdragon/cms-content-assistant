"""Allowlisted tool registry: the only way the agent can touch data.

Every call goes through `execute`, which:
- rejects tools that are not registered (allowlist);
- validates arguments against the tool's Pydantic model (unknown keys rejected);
- enforces a timeout and a maximum serialized output size;
- maps domain errors to typed statuses without leaking internals;
- writes one activity-log event per call, with arguments redacted.
"""

import json
import logging
import time
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any

from pydantic import BaseModel, ValidationError

from app.errors import ConflictError, DomainError, InvalidInputError, NotFoundError
from app.models.activity import Actor, EventType
from app.services.audit import AuditService
from app.tools.base import Tool, ToolContext, ToolExecution, ToolStatus

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_MAX_OUTPUT_BYTES = 64_000

_STATUS_FOR_ERROR: dict[type[DomainError], ToolStatus] = {
    NotFoundError: ToolStatus.NOT_FOUND,
    ConflictError: ToolStatus.CONFLICT,
    InvalidInputError: ToolStatus.INVALID_ARGUMENTS,
}


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:5]:
        loc = ".".join(str(p) for p in err["loc"]) or "arguments"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def _summarize(output: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in ("findings", "matches", "groups"):
        if isinstance(output.get(key), list):
            summary[f"{key}_count"] = len(output[key])
    for key in ("total_found", "truncated", "proposal_id", "content_id"):
        if key in output:
            summary[key] = output[key]
    return summary


class ToolRegistry:
    def __init__(
        self,
        tools: Iterable[Tool[Any, Any]],
        audit: AuditService,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
    ) -> None:
        self._tools: dict[str, Tool[Any, Any]] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"duplicate tool name: {tool.name}")
            self._tools[tool.name] = tool
        self._audit = audit
        self._timeout = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="tool")

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> Tool[Any, Any] | None:
        return self._tools.get(name)

    def describe(self) -> list[dict[str, Any]]:
        """Tool specs (name, description, kind, JSON schema) for UIs and model providers."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "kind": t.kind.value,
                "input_schema": t.json_schema(),
            }
            for t in (self._tools[n] for n in self.names)
        ]

    def execute(
        self,
        name: str,
        arguments: Mapping[str, Any] | None,
        ctx: ToolContext,
        *,
        actor: Actor = Actor.ASSISTANT,
    ) -> ToolExecution:
        started = time.monotonic()
        raw_args: Any = {} if arguments is None else arguments
        status, output, error = self._run(name, raw_args, ctx)
        execution = ToolExecution(
            tool_name=name,
            status=status,
            output=output,
            error=error,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
        self._audit.record(
            EventType.TOOL_CALL,
            actor=actor,
            tool_name=name,
            status=status.value,
            details={
                "arguments": dict(raw_args) if isinstance(raw_args, Mapping) else repr(raw_args),
                "duration_ms": execution.duration_ms,
                **({"error": error} if error else {}),
                **({"result": _summarize(output)} if output else {}),
            },
        )
        return execution

    def _run(
        self, name: str, raw_args: Any, ctx: ToolContext
    ) -> tuple[ToolStatus, dict[str, Any] | None, str | None]:
        tool = self._tools.get(name)
        if tool is None:
            return ToolStatus.UNKNOWN_TOOL, None, f"Unknown tool '{name}'. Allowed: {self.names}"
        if not isinstance(raw_args, Mapping):
            return ToolStatus.INVALID_ARGUMENTS, None, "arguments must be a JSON object"

        try:
            args = tool.input_model.model_validate(dict(raw_args))
        except ValidationError as exc:
            return ToolStatus.INVALID_ARGUMENTS, None, _format_validation_error(exc)

        future = self._executor.submit(tool.handler, ctx, args)
        try:
            result: BaseModel = future.result(timeout=self._timeout)
        except FutureTimeout:
            future.cancel()
            return ToolStatus.TIMEOUT, None, f"Tool timed out after {self._timeout:g}s"
        except DomainError as exc:
            return _STATUS_FOR_ERROR.get(type(exc), ToolStatus.ERROR), None, exc.message
        except Exception:
            logger.exception("Tool %s failed", name)
            return ToolStatus.ERROR, None, "The tool failed unexpectedly. Unable to verify."

        output = result.model_dump(mode="json")
        size = len(json.dumps(output))
        if size > self._max_output_bytes:
            return (
                ToolStatus.OUTPUT_TOO_LARGE,
                None,
                f"Output was {size} bytes (limit {self._max_output_bytes}). Narrow the query.",
            )
        return ToolStatus.OK, output, None
