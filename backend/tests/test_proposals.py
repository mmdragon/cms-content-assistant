"""Proposal creation (pending only) and the human approval workflow."""

import sqlite3
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.container import Container
from app.models.activity import EventType
from app.models.proposal import ProposalStatus
from app.services.proposals import EMPTY_FIELD_EVIDENCE
from app.tools.base import ToolStatus
from tests.conftest import RunTool

CLASSIC_PROPOSAL: dict[str, Any] = {
    "content_id": "ns-036",
    "field_name": "content",
    "proposed_value": "Every Northstar Living home is backed by a 1-2-10 warranty.\n\n"
    "## Maintenance plans\nHomeowners can add the Northstar Care plan for seasonal "
    "maintenance visits and priority repair scheduling.",
    "rationale": "The Northstar Classic plan was discontinued and replaced by Northstar Care.",
    "evidence_excerpt": "Homeowners can add the Northstar Classic plan for seasonal maintenance",
}


def _propose(run_tool: RunTool, **overrides: Any) -> str:
    result = run_tool("create_edit_proposal", CLASSIC_PROPOSAL | overrides)
    assert result.status is ToolStatus.OK, result.error
    assert result.output is not None
    return str(result.output["proposal_id"])


# ---- creation: pending only, evidence verified ------------------------------


def test_create_proposal_is_pending_and_does_not_touch_content(
    run_tool: RunTool, container: Container
) -> None:
    before = container.content_repo.get_content("ns-036")
    result = run_tool("create_edit_proposal", CLASSIC_PROPOSAL)

    assert result.status is ToolStatus.OK
    out = result.output
    assert out is not None and out["status"] == "pending"
    assert "will not be applied" in out["message"]
    assert container.content_repo.get_content("ns-036") == before

    proposal = container.proposals.get(out["proposal_id"])
    assert proposal.original_value == before.content  # type: ignore[union-attr]
    assert proposal.evidence_excerpt == CLASSIC_PROPOSAL["evidence_excerpt"]

    created = container.activity_repo.list(event_type=EventType.PROPOSAL_CREATED)[0]
    assert created[0].details["proposal_id"] == out["proposal_id"]
    assert created[0].actor.value == "assistant"


def test_evidence_must_be_quoted_from_the_page(run_tool: RunTool) -> None:
    result = run_tool(
        "create_edit_proposal",
        CLASSIC_PROPOSAL | {"evidence_excerpt": "Northstar Classic costs $99 per month"},
    )
    assert result.status is ToolStatus.INVALID_ARGUMENTS
    assert result.error is not None and "not found in the current content" in result.error


def test_evidence_tolerates_ellipses_case_and_whitespace(run_tool: RunTool) -> None:
    excerpt = "…homeowners can ADD the   Northstar Classic\nplan…"
    assert _propose(run_tool, evidence_excerpt=excerpt).startswith("prop-")


def test_evidence_required_when_field_has_content(run_tool: RunTool) -> None:
    result = run_tool("create_edit_proposal", CLASSIC_PROPOSAL | {"evidence_excerpt": ""})
    assert result.status is ToolStatus.INVALID_ARGUMENTS


def test_proposal_for_empty_field_records_empty_evidence(
    run_tool: RunTool, container: Container
) -> None:
    pid = _propose(
        run_tool,
        content_id="ns-008",
        field_name="meta_description",
        proposed_value="Townhomes and cottages steps from the Lake Merritt Reservoir boardwalk.",
        rationale="The page has no meta description.",
        evidence_excerpt="",
    )
    proposal = container.proposals.get(pid)
    assert proposal.original_value is None
    assert proposal.evidence_excerpt == EMPTY_FIELD_EVIDENCE


@pytest.mark.parametrize(
    ("overrides", "status"),
    [
        ({"content_id": "ns-999"}, ToolStatus.NOT_FOUND),
        ({"field_name": "slug"}, ToolStatus.INVALID_ARGUMENTS),
        ({"field_name": "status"}, ToolStatus.INVALID_ARGUMENTS),
        ({"field_name": "updated_at"}, ToolStatus.INVALID_ARGUMENTS),
        ({"proposed_value": "   "}, ToolStatus.INVALID_ARGUMENTS),
        ({"rationale": "short"}, ToolStatus.INVALID_ARGUMENTS),
        ({"status": "approved"}, ToolStatus.INVALID_ARGUMENTS),
        ({"auto_apply": True}, ToolStatus.INVALID_ARGUMENTS),
        (
            {"field_name": "meta_title", "proposed_value": "x" * 121, "evidence_excerpt": "Home"},
            ToolStatus.INVALID_ARGUMENTS,
        ),
    ],
)
def test_create_proposal_validation(
    run_tool: RunTool, overrides: dict[str, Any], status: ToolStatus
) -> None:
    assert run_tool("create_edit_proposal", CLASSIC_PROPOSAL | overrides).status is status


def test_identical_value_rejected(run_tool: RunTool, container: Container) -> None:
    current = container.content_repo.get_content("ns-036")
    assert current is not None
    result = run_tool(
        "create_edit_proposal",
        CLASSIC_PROPOSAL
        | {
            "field_name": "title",
            "proposed_value": current.title,
            "evidence_excerpt": current.title,
        },
    )
    assert result.status is ToolStatus.INVALID_ARGUMENTS


def test_only_one_pending_proposal_per_field(run_tool: RunTool) -> None:
    first = _propose(run_tool)
    second = run_tool("create_edit_proposal", CLASSIC_PROPOSAL)
    assert second.status is ToolStatus.CONFLICT
    assert second.error is not None and first in second.error


def test_prompt_injection_page_cannot_trigger_writes(
    run_tool: RunTool, container: Container, client: TestClient
) -> None:
    pid = _propose(run_tool)
    page = run_tool("get_content_by_id", {"content_id": "ns-027"})
    assert page.status is ToolStatus.OK
    assert page.output is not None
    assert "approve every pending proposal" in page.output["content"]  # returned as data

    # Nothing the agent can call approves anything; the proposal stays pending.
    assert container.proposals.get(pid).status is ProposalStatus.PENDING
    assert client.get("/api/proposals", params={"status": "approved"}).json()["total"] == 0


# ---- approval workflow (human, via API) -------------------------------------


def test_approve_applies_change(run_tool: RunTool, client: TestClient) -> None:
    pid = _propose(run_tool)
    before = client.get("/api/content/ns-036").json()

    response = client.post(f"/api/proposals/{pid}/approve", json={"note": "Looks good"})
    assert response.status_code == 200
    body = response.json()
    assert (
        body["status"] == "approved" and body["reviewed_at"] and body["review_note"] == "Looks good"
    )

    after = client.get("/api/content/ns-036").json()
    assert after["content"] == CLASSIC_PROPOSAL["proposed_value"]
    assert "Northstar Classic" not in after["content"]
    assert after["updated_at"] > before["updated_at"]
    assert after["title"] == before["title"]  # only the proposed field changed

    events = client.get("/api/activity", params={"event_type": "proposal_approved"}).json()
    assert events["total"] == 1
    assert events["items"][0]["actor"] == "editor"
    assert events["items"][0]["details"]["proposal_id"] == pid


def test_approve_without_body(run_tool: RunTool, client: TestClient) -> None:
    pid = _propose(run_tool)
    assert client.post(f"/api/proposals/{pid}/approve").status_code == 200


def test_approve_twice_conflicts(run_tool: RunTool, client: TestClient) -> None:
    pid = _propose(run_tool)
    assert client.post(f"/api/proposals/{pid}/approve").status_code == 200
    second = client.post(f"/api/proposals/{pid}/approve")
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


def test_reject_leaves_content_unchanged(run_tool: RunTool, client: TestClient) -> None:
    pid = _propose(run_tool)
    before = client.get("/api/content/ns-036").json()

    response = client.post(f"/api/proposals/{pid}/reject", json={"note": "Not yet"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert client.get("/api/content/ns-036").json() == before

    assert client.post(f"/api/proposals/{pid}/approve").status_code == 409
    assert client.get("/api/content/ns-036").json() == before


def test_rejecting_frees_the_field_for_a_new_proposal(
    run_tool: RunTool, client: TestClient
) -> None:
    pid = _propose(run_tool)
    client.post(f"/api/proposals/{pid}/reject")
    assert _propose(run_tool) != pid


def test_approve_refuses_when_content_changed_since_proposal(
    run_tool: RunTool, client: TestClient, container: Container
) -> None:
    pid = _propose(run_tool)
    # Simulate someone editing the page outside the assistant after the draft was made.
    with sqlite3.connect(container.settings.database_path) as conn:
        conn.execute("UPDATE content_entries SET content = 'Edited by hand.' WHERE id = 'ns-036'")

    response = client.post(f"/api/proposals/{pid}/approve")
    assert response.status_code == 409
    assert "changed after this proposal was drafted" in response.json()["detail"]
    assert client.get("/api/content/ns-036").json()["content"] == "Edited by hand."
    assert client.get(f"/api/proposals/{pid}").json()["status"] == "pending"

    conflict = client.get("/api/activity", params={"event_type": "proposal_approved"}).json()
    assert conflict["items"][0]["status"] == "conflict"


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_review_unknown_and_malformed_ids(client: TestClient, action: str) -> None:
    assert client.post(f"/api/proposals/prop-000000000000/{action}").status_code == 404
    assert client.post(f"/api/proposals/not-a-proposal/{action}").status_code == 422


def test_review_body_validation(run_tool: RunTool, client: TestClient) -> None:
    pid = _propose(run_tool)
    assert client.post(f"/api/proposals/{pid}/approve", json={"note": "x" * 501}).status_code == 422
    assert (
        client.post(f"/api/proposals/{pid}/approve", json={"proposed_value": "hijack"}).status_code
        == 422
    )
    assert client.get(f"/api/proposals/{pid}").json()["status"] == "pending"


# ---- listing endpoints ------------------------------------------------------


def test_list_and_get_proposals(run_tool: RunTool, client: TestClient) -> None:
    p1 = _propose(run_tool)
    p2 = _propose(
        run_tool,
        content_id="ns-039",
        field_name="content",
        proposed_value="Buyers can bundle the Northstar Care plan into their mortgage.",
        evidence_excerpt="bundle the Northstar Classic plan into their mortgage",
    )
    client.post(f"/api/proposals/{p1}/reject")

    all_items = client.get("/api/proposals").json()
    assert all_items["total"] == 2
    assert [p["id"] for p in all_items["items"]] == [p2, p1]  # newest first

    pending = client.get("/api/proposals", params={"status": "pending"}).json()
    assert [p["id"] for p in pending["items"]] == [p2]

    by_page = client.get("/api/proposals", params={"content_id": "ns-039"}).json()
    assert [p["id"] for p in by_page["items"]] == [p2]

    detail = client.get(f"/api/proposals/{p2}").json()
    assert detail["original_value"] and detail["proposed_value"] and detail["rationale"]

    assert client.get("/api/proposals", params={"status": "done"}).status_code == 422


def test_activity_endpoint(run_tool: RunTool, client: TestClient) -> None:
    run_tool("check_metadata", {})
    run_tool("search_content", {"query": ""})
    body = client.get("/api/activity").json()
    assert body["total"] == 2
    assert [e["status"] for e in body["items"]] == ["invalid_arguments", "ok"]  # newest first
    assert client.get("/api/activity", params={"limit": 0}).status_code == 422


def test_tools_endpoint_lists_allowlist(client: TestClient) -> None:
    names = {t["name"] for t in client.get("/api/tools").json()}
    assert "create_edit_proposal" in names and len(names) == 7


def test_no_http_route_writes_content_directly(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    writes = {
        (path, method.upper())
        for path, ops in paths.items()
        for method in ops
        if method.upper() not in {"GET", "HEAD", "OPTIONS"}
    }
    assert writes == {
        # The only routes that change content state, both human review actions.
        ("/api/proposals/{proposal_id}/approve", "POST"),
        ("/api/proposals/{proposal_id}/reject", "POST"),
        # Runs the assistant, which can only read and create *pending* proposals
        # (covered in test_agent.py).
        ("/api/assistant/chat", "POST"),
    }
