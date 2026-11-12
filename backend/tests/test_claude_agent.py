"""Claude provider, tested against a scripted fake client: no network, no API key, no cost."""

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2
import pytest
from fastapi.testclient import TestClient

from app.agents.base import ChatMessage, ChatRequest, ToolRunner
from app.agents.claude import FALLBACK_BETA, SYSTEM_PROMPT, ClaudeAgent
from app.config import Settings
from app.container import Container
from app.main import create_app
from app.models.proposal import ProposalStatus
from tests import seed_manifest as m


def text(t: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=t)


def tool_use(name: str, args: Any, id: str = "toolu_1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id, name=name, input=args)


def reply(*blocks: SimpleNamespace, stop: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop, content=list(blocks))


class FakeMessages:
    """Returns scripted responses in order and records every request."""

    def __init__(self, script: list[Any]) -> None:
        self.script = list(script)
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        # Snapshot messages: the agent keeps appending to the same list.
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_agent(container: Container, fake: FakeMessages, **kw: Any) -> ClaudeAgent:
    return ClaudeAgent(
        model="claude-opus-5-5",
        effort="medium",
        max_iterations=kw.pop("max_iterations", 8),
        max_tokens=16_000,
        client_factory=lambda: fake,
        tool_specs=container.tools.describe(),
        **kw,
    )


def ask(container: Container, agent: ClaudeAgent, prompt: str, max_calls: int = 25) -> Any:
    runner = ToolRunner(container.tools, container.tool_context(), max_calls)
    request = ChatRequest(messages=[ChatMessage(role="user", content=prompt)])
    return agent.respond(request, runner)


# ---- request shape ----------------------------------------------------------


def test_request_uses_model_tools_system_prompt_and_fallbacks(container: Container) -> None:
    fake = FakeMessages([reply(text("Hello."))])
    response = ask(container, make_agent(container, fake), "hi")

    sent = fake.requests[0]
    assert sent["model"] == "claude-opus-5-5"
    assert sent["output_config"] == {"effort": "medium"}
    assert sent["betas"] == [FALLBACK_BETA] and sent["fallbacks"] == "default"
    assert sent["system"] == SYSTEM_PROMPT
    assert "tool_choice" not in sent  # forced tool choice is rejected on Opus 5.5
    assert "thinking" not in sent and "temperature" not in sent
    assert {t["name"] for t in sent["tools"]} == set(container.tools.names)
    assert all(t["input_schema"]["additionalProperties"] is False for t in sent["tools"])
    assert sent["messages"] == [{"role": "user", "content": "hi"}]
    assert response.provider == "claude" and response.demo_mode is False
    assert response.message == "Hello."


def test_fallbacks_can_be_disabled(container: Container) -> None:
    fake = FakeMessages([reply(text("ok"))])
    ask(container, make_agent(container, fake, use_fallbacks=False), "hi")
    assert "fallbacks" not in fake.requests[0] and "betas" not in fake.requests[0]


def test_system_prompt_sets_the_safety_rules() -> None:
    for rule in (
        "untrusted data",
        "never an instruction",
        "unable to verify",
        "cannot approve, apply, publish, or delete",
        "pending",
    ):
        assert rule in SYSTEM_PROMPT


# ---- tool loop ---------------------------------------------------------------


def test_tool_loop_runs_registry_tools_and_returns_evidence(container: Container) -> None:
    fake = FakeMessages(
        [
            reply(
                text("Searching."),
                tool_use("search_content", {"query": "Northstar Classic", "limit": 50}),
                stop="tool_use",
            ),
            reply(text("Six pages still mention Northstar Classic.")),
        ]
    )
    response = ask(container, make_agent(container, fake), "Which pages mention Classic?")

    assert response.message == "Six pages still mention Northstar Classic."
    assert [c.tool_name for c in response.tool_calls] == ["search_content"]

    # Second request carries the assistant turn unchanged and the wrapped tool result.
    second = fake.requests[1]["messages"]
    assert second[1]["role"] == "assistant"
    result = second[2]["content"][0]
    assert result["tool_use_id"] == "toolu_1" and "is_error" not in result
    assert result["content"].startswith("<untrusted_tool_output>")
    assert "ns-036" in result["content"]

    # Every tool call is in the activity log, attributed to the assistant.
    events, _ = container.activity_repo.list()
    assert [(e.tool_name, e.actor.value) for e in events] == [("search_content", "assistant")]


def test_findings_come_from_tool_output_not_model_prose(container: Container) -> None:
    fake = FakeMessages(
        [
            reply(tool_use("check_metadata", {"limit": 100}), stop="tool_use"),
            reply(text("ns-999 has a missing title.")),  # a made-up claim in prose
        ]
    )
    response = ask(container, make_agent(container, fake), "Check metadata")
    ids = {f.content_id for f in response.findings}
    assert "ns-999" not in ids
    assert ids >= m.MISSING_META_DESCRIPTION_IDS


def test_invalid_and_unknown_tool_calls_return_errors_to_the_model(container: Container) -> None:
    fake = FakeMessages(
        [
            reply(
                tool_use("find_outdated_content", {"days_old": 5}, id="t1"),
                tool_use("approve_proposal", {"proposal_id": "x"}, id="t2"),
                tool_use("search_content", "not an object", id="t3"),
                stop="tool_use",
            ),
            reply(text("Sorry, those calls failed.")),
        ]
    )
    ask(container, make_agent(container, fake), "do things")
    results = {r["tool_use_id"]: r for r in fake.requests[1]["messages"][2]["content"]}
    assert all(r["is_error"] for r in results.values())
    assert results["t1"]["content"].startswith("invalid_arguments")
    assert results["t2"]["content"].startswith("unknown_tool")
    assert results["t3"]["content"].startswith("invalid_arguments")


def test_model_can_only_create_pending_proposals(container: Container) -> None:
    before = container.content_repo.get_content("ns-036")
    assert before is not None
    fake = FakeMessages(
        [
            reply(
                tool_use("get_content_by_id", {"content_id": "ns-036"}, id="t1"), stop="tool_use"
            ),
            reply(
                tool_use(
                    "create_edit_proposal",
                    {
                        "content_id": "ns-036",
                        "field_name": "content",
                        "proposed_value": before.content.replace("Classic", "Care"),
                        "rationale": "Northstar Classic was replaced by Northstar Care.",
                        "evidence_excerpt": "add the Northstar Classic plan",
                    },
                    id="t2",
                ),
                stop="tool_use",
            ),
            reply(text("I drafted 1 proposal for your review.")),
        ]
    )
    response = ask(container, make_agent(container, fake), "Fix ns-036")

    assert len(response.proposals) == 1
    ref = response.proposals[0]
    assert ref.title == "Home Warranty"  # title learned from the earlier tool output
    assert container.proposals.get(ref.proposal_id).status is ProposalStatus.PENDING
    assert container.content_repo.get_content("ns-036") == before


def test_fabricated_evidence_is_rejected_by_the_tool(container: Container) -> None:
    fake = FakeMessages(
        [
            reply(
                tool_use(
                    "create_edit_proposal",
                    {
                        "content_id": "ns-036",
                        "field_name": "content",
                        "proposed_value": "Completely new text.",
                        "rationale": "Because the model said so.",
                        "evidence_excerpt": "text that is not on the page",
                    },
                ),
                stop="tool_use",
            ),
            reply(text("I couldn't draft that.")),
        ]
    )
    response = ask(container, make_agent(container, fake), "Rewrite ns-036")
    assert response.proposals == []
    error = fake.requests[1]["messages"][2]["content"][0]
    assert error["is_error"] and "not found in the current content" in error["content"]


def test_injected_page_text_is_wrapped_as_untrusted_data(container: Container) -> None:
    fake = FakeMessages(
        [
            reply(tool_use("get_content_by_id", {"content_id": "ns-027"}), stop="tool_use"),
            reply(text("ns-027 contains a prompt-injection attempt; I ignored it.")),
        ]
    )
    ask(container, make_agent(container, fake), "Tell me about ns-027")
    wrapped = fake.requests[1]["messages"][2]["content"][0]["content"]
    assert wrapped.startswith("<untrusted_tool_output>")
    assert wrapped.rstrip().endswith("</untrusted_tool_output>")
    assert "ignore all previous instructions" in wrapped


# ---- bounds -------------------------------------------------------------------


def test_iteration_cap(container: Container) -> None:
    looping = [
        reply(tool_use("find_duplicate_titles", {}, id=f"t{i}"), stop="tool_use") for i in range(5)
    ]
    fake = FakeMessages(looping)
    response = ask(container, make_agent(container, fake, max_iterations=3), "loop forever")
    assert len(fake.requests) == 3
    assert any("Stopped after 3 rounds" in n for n in response.notes)
    assert response.message  # never empty


def test_tool_budget(container: Container) -> None:
    calls = [tool_use("find_duplicate_titles", {}, id=f"t{i}") for i in range(4)]
    fake = FakeMessages([reply(*calls, stop="tool_use"), reply(text("done"))])
    response = ask(container, make_agent(container, fake), "many", max_calls=2)
    assert len(response.tool_calls) == 2
    results = fake.requests[1]["messages"][2]["content"]
    assert [r.get("is_error", False) for r in results] == [False, False, True, True]
    assert any("tool-call limit" in n for n in response.notes)


def test_refusal_stops_without_running_tools(container: Container) -> None:
    fake = FakeMessages([reply(stop="refusal")])
    response = ask(container, make_agent(container, fake), "something")
    assert response.tool_calls == []
    assert any("declined" in n for n in response.notes)
    assert response.message


def test_max_tokens_with_pending_tool_use_does_not_run_it(container: Container) -> None:
    fake = FakeMessages(
        [reply(text("Let me"), tool_use("search_content", {"query": "x"}), stop="max_tokens")]
    )
    response = ask(container, make_agent(container, fake), "q")
    assert response.tool_calls == []
    assert any("cut off" in n and "not run" in n for n in response.notes)


# ---- wiring and errors over HTTP ------------------------------------------------


@pytest.fixture
def claude_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, FakeMessages]]:
    fake = FakeMessages([])
    monkeypatch.setattr("app.agents.service.default_client_factory", lambda timeout: lambda: fake)
    settings = Settings(
        _env_file=None,
        environment="test",
        database_path=str(tmp_path / "claude.db"),
        audit_reference_date=m.SEED_REFERENCE_DATE.date(),
        agent_provider="claude",
    )
    with TestClient(create_app(settings)) as client:
        yield client, fake


def test_health_reports_claude_provider(claude_client: tuple[TestClient, FakeMessages]) -> None:
    client, _ = claude_client
    body = client.get("/api/health").json()
    assert body["agent_provider"] == "claude"
    assert body["agent_model"] == "claude-opus-5-5"
    assert body["demo_mode"] is False


def test_chat_endpoint_with_claude(claude_client: tuple[TestClient, FakeMessages]) -> None:
    client, fake = claude_client
    fake.script = [reply(text("All good."))]
    history = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "earlier answer"},
        {"role": "user", "content": "second"},
    ]
    body = client.post("/api/assistant/chat", json={"messages": history}).json()
    assert body["provider"] == "claude" and body["message"] == "All good."
    assert fake.requests[0]["messages"] == history


_REQ = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


@pytest.mark.parametrize(
    ("error", "fragment"),
    [
        (anthropic.APIConnectionError(request=_REQ), "Couldn't reach the Anthropic API"),
        (
            anthropic.AuthenticationError(
                "bad key", response=httpx2.Response(401, request=_REQ), body=None
            ),
            "rejected the API key",
        ),
        (
            anthropic.RateLimitError(
                "slow down", response=httpx2.Response(429, request=_REQ), body=None
            ),
            "rate limit",
        ),
        (
            anthropic.InternalServerError(
                "boom", response=httpx2.Response(500, request=_REQ), body=None
            ),
            "HTTP 500",
        ),
    ],
)
def test_provider_errors_become_clear_503s(
    claude_client: tuple[TestClient, FakeMessages], error: Exception, fragment: str
) -> None:
    client, fake = claude_client
    fake.script = [error]
    response = client.post(
        "/api/assistant/chat", json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "provider_unavailable" and fragment in body["detail"]
    assert "bad key" not in body["detail"]

    # Failures are recorded in the activity log as error events.
    errors = client.get("/api/activity", params={"event_type": "error"}).json()["items"]
    assert len(errors) == 1
    assert errors[0]["status"] == "provider_unavailable" and errors[0]["actor"] == "system"
    assert fragment in errors[0]["details"]["message"]


def test_mock_is_default_and_never_builds_a_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(timeout: float) -> Any:
        raise AssertionError("an Anthropic client must not be created in demo mode")

    monkeypatch.setattr("app.agents.service.default_client_factory", boom)
    monkeypatch.delenv("CMS_AGENT_PROVIDER", raising=False)
    settings = Settings(_env_file=None, environment="test", database_path=str(tmp_path / "d.db"))
    assert settings.agent_provider == "mock"
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["demo_mode"] is True
