"""Registry guarantees: allowlist, timeouts, error mapping, output limits, audit logging."""

import time
from typing import Any

import pytest
from pydantic import BaseModel

from app.container import Container
from app.models.activity import EventType
from app.services.audit import REDACTED, redact
from app.tools import build_default_registry
from app.tools.base import Tool, ToolContext, ToolInput, ToolKind, ToolStatus
from app.tools.content_tools import SEARCH_CONTENT
from app.tools.registry import ToolRegistry
from tests.conftest import RunTool

EXPECTED_TOOLS = {
    "search_content",
    "get_content_by_id",
    "find_outdated_content",
    "find_duplicate_titles",
    "check_metadata",
    "check_internal_links",
    "create_edit_proposal",
}


def test_allowlist_is_exact(container: Container) -> None:
    assert set(container.tools.names) == EXPECTED_TOOLS


def test_no_tool_can_apply_or_delete(container: Container) -> None:
    forbidden = ("approve", "apply", "update", "delete", "publish", "write", "sql", "reject")
    for name in container.tools.names:
        assert not any(word in name for word in forbidden), name
    kinds = {t["name"]: t["kind"] for t in container.tools.describe()}
    assert {n for n, k in kinds.items() if k != ToolKind.READ} == {"create_edit_proposal"}


def test_describe_exposes_strict_schemas(container: Container) -> None:
    specs = {s["name"]: s for s in container.tools.describe()}
    schema = specs["search_content"]["input_schema"]
    assert schema["required"] == ["query"]
    assert schema["additionalProperties"] is False
    proposal_props = specs["create_edit_proposal"]["input_schema"]["properties"]
    assert set(proposal_props["field_name"]["$ref"].split("/")[-1:]) == {"EditableField"}


def test_unknown_tool_is_rejected_and_logged(run_tool: RunTool, container: Container) -> None:
    result = run_tool("delete_all_content", {"confirm": True})
    assert result.status is ToolStatus.UNKNOWN_TOOL
    assert result.error is not None and "Allowed" in result.error

    events, _ = container.activity_repo.list(event_type=EventType.TOOL_CALL)
    assert events[0].tool_name == "delete_all_content"
    assert events[0].status == "unknown_tool"


def test_every_call_is_logged_with_summary(run_tool: RunTool, container: Container) -> None:
    run_tool("search_content", {"query": "Northstar Classic"})
    events, total = container.activity_repo.list()
    assert total == 1
    event = events[0]
    assert event.event_type is EventType.TOOL_CALL
    assert event.actor.value == "assistant"
    assert event.status == "ok"
    assert event.details["arguments"] == {"query": "Northstar Classic"}
    assert event.details["result"] == {"matches_count": 6, "total_found": 6, "truncated": False}
    assert isinstance(event.details["duration_ms"], int)


def test_logged_arguments_are_redacted(run_tool: RunTool, container: Container) -> None:
    run_tool(
        "search_content",
        {"query": "x", "api_key": "sk-ant-abcdefghijklmnopqrstuvwxyz", "note": "Bearer abc.def"},
    )
    event = container.activity_repo.list()[0][0]
    args = event.details["arguments"]
    assert args["api_key"] == REDACTED
    assert args["note"] == REDACTED
    assert "sk-ant" not in str(event.details)


def test_redact_truncates_long_values() -> None:
    data = {"text": "a" * 2000, "items": list(range(80)), "nested": {"password": "hunter2"}}
    safe = redact(data)
    assert len(safe["text"]) < 600 and safe["text"].endswith("chars truncated]")
    assert len(safe["items"]) == 51
    assert safe["nested"]["password"] == REDACTED


class _Empty(ToolInput):
    pass


class _Out(BaseModel):
    value: str


def _registry_with(container: Container, handler: Any, **kwargs: Any) -> ToolRegistry:
    tool = Tool(
        name="test_tool",
        description="test",
        kind=ToolKind.READ,
        input_model=_Empty,
        output_model=_Out,
        handler=handler,
    )
    return ToolRegistry([tool], container.audit, **kwargs)


def test_timeout(container: Container, ctx: ToolContext) -> None:
    def slow(_ctx: ToolContext, _args: _Empty) -> _Out:
        time.sleep(0.5)
        return _Out(value="late")

    registry = _registry_with(container, slow, timeout_seconds=0.05)
    result = registry.execute("test_tool", {}, ctx)
    assert result.status is ToolStatus.TIMEOUT
    assert result.output is None


def test_unexpected_exception_does_not_leak_details(container: Container, ctx: ToolContext) -> None:
    def boom(_ctx: ToolContext, _args: _Empty) -> _Out:
        raise RuntimeError("database password is hunter2")

    result = _registry_with(container, boom).execute("test_tool", {}, ctx)
    assert result.status is ToolStatus.ERROR
    assert result.error is not None
    assert "hunter2" not in result.error and "Unable to verify" in result.error


def test_output_size_limit(container: Container, ctx: ToolContext) -> None:
    registry = build_default_registry(container.audit, max_output_bytes=500)
    result = registry.execute("search_content", {"query": "Northstar", "limit": 50}, ctx)
    assert result.status is ToolStatus.OUTPUT_TOO_LARGE
    assert result.output is None
    assert result.error is not None and "Narrow the query" in result.error


def test_duplicate_tool_names_rejected(container: Container) -> None:
    with pytest.raises(ValueError, match="duplicate tool name"):
        ToolRegistry([SEARCH_CONTENT, SEARCH_CONTENT], container.audit)
