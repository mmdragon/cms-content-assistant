"""Read-only tools against the seed dataset: exact, deterministic results."""

from pathlib import Path
from typing import Any

import pytest

from app.models.content import ContentEntry
from app.repositories.activity import SQLiteActivityRepository
from app.repositories.proposals import SQLiteProposalRepository
from app.repositories.sqlite import SQLiteContentRepository
from app.services.audit import AuditService
from app.services.proposals import ProposalService
from app.tools import build_default_registry
from app.tools.base import ToolContext, ToolStatus
from app.tools.findings import excerpt_around, find_excerpt
from tests import seed_manifest as m
from tests.conftest import RunTool

# ---- search_content ---------------------------------------------------------


def test_search_finds_discontinued_plan_with_evidence(run_tool: RunTool) -> None:
    result = run_tool("search_content", {"query": "Northstar Classic", "limit": 50})

    assert result.status is ToolStatus.OK
    out = result.output
    assert out is not None
    assert {mt["content_id"] for mt in out["matches"]} == m.DISCONTINUED_TERM_IDS
    assert out["total_found"] == 6 and out["truncated"] is False
    for match in out["matches"]:
        assert "northstar classic" in match["excerpt"].lower()
        assert match["matched_fields"]


def test_search_reports_truncation(run_tool: RunTool) -> None:
    out = run_tool("search_content", {"query": "Northstar Classic", "limit": 2}).output
    assert out is not None
    assert len(out["matches"]) == 2
    assert out["total_found"] == 6 and out["truncated"] is True


def test_search_filters_and_empty_results(run_tool: RunTool) -> None:
    out = run_tool("search_content", {"query": "Northstar Classic", "category": "faq"}).output
    assert out is not None and [mt["content_id"] for mt in out["matches"]] == ["ns-033"]

    empty = run_tool("search_content", {"query": "zeppelin"})
    assert empty.status is ToolStatus.OK
    assert empty.output == {
        "query": "zeppelin",
        "total_found": 0,
        "truncated": False,
        "matches": [],
    }


def test_search_treats_sql_as_plain_text(run_tool: RunTool) -> None:
    result = run_tool("search_content", {"query": "'; DROP TABLE content_entries; --"})
    assert result.status is ToolStatus.OK
    assert result.output is not None and result.output["total_found"] == 0
    assert run_tool("search_content", {"query": "Cedar"}).output["total_found"] > 0  # type: ignore[index]


@pytest.mark.parametrize(
    "args",
    [
        None,
        {},
        {"query": ""},
        {"query": "   "},
        {"query": "x" * 201},
        {"query": "ok", "limit": 0},
        {"query": "ok", "limit": 51},
        {"query": "ok", "limit": "ten"},
        {"query": "ok", "category": "press-release"},
        {"query": "ok", "unexpected": True},
        ["query", "ok"],
        "query=ok",
    ],
)
def test_search_rejects_invalid_arguments(run_tool: RunTool, args: Any) -> None:
    result = run_tool("search_content", args)
    assert result.status is ToolStatus.INVALID_ARGUMENTS
    assert result.output is None and result.error


# ---- get_content_by_id ------------------------------------------------------


def test_get_content_by_id(run_tool: RunTool) -> None:
    out = run_tool("get_content_by_id", {"content_id": "ns-036"}).output
    assert out is not None
    assert out["title"] == "Home Warranty"
    assert "Northstar Classic" in out["content"]
    assert out["content_truncated"] is False


def test_get_content_by_id_not_found_says_unable_to_verify(run_tool: RunTool) -> None:
    result = run_tool("get_content_by_id", {"content_id": "ns-999"})
    assert result.status is ToolStatus.NOT_FOUND
    assert result.error is not None and "Unable to verify" in result.error


@pytest.mark.parametrize("bad", [{"content_id": "NS-001"}, {"content_id": ""}, {"id": "ns-001"}])
def test_get_content_by_id_invalid(run_tool: RunTool, bad: dict[str, str]) -> None:
    assert run_tool("get_content_by_id", bad).status is ToolStatus.INVALID_ARGUMENTS


# ---- find_outdated_content --------------------------------------------------


def test_find_outdated_default_threshold_matches_manifest(run_tool: RunTool) -> None:
    out = run_tool("find_outdated_content", {}).output
    assert out is not None
    assert out["as_of"] == "2026-11-12"
    assert out["cutoff"] == "2025-05-21"  # 540 days earlier
    ids = [f["content_id"] for f in out["findings"]]
    assert set(ids) == m.STALE_IDS
    stamps = [f["excerpt"].split()[2] for f in out["findings"]]
    assert stamps == sorted(stamps), "oldest first"
    for f in out["findings"]:
        assert f["issue"] == "stale_content" and f["field"] == "updated_at"
        assert f["reason"] and f["recommendation"]


def test_find_outdated_filters_and_thresholds(run_tool: RunTool) -> None:
    archived = run_tool("find_outdated_content", {"status": "archived"}).output
    assert archived is not None and [f["content_id"] for f in archived["findings"]] == ["ns-038"]

    none = run_tool("find_outdated_content", {"days_old": 3650}).output
    assert none is not None and none["findings"] == [] and none["total_found"] == 0

    capped = run_tool("find_outdated_content", {"limit": 2}).output
    assert capped is not None
    assert len(capped["findings"]) == 2 and capped["truncated"] and capped["total_found"] == 6


def test_find_outdated_marks_very_old_pages_high_severity(run_tool: RunTool) -> None:
    out = run_tool("find_outdated_content", {"days_old": 365}).output
    assert out is not None
    severity = {f["content_id"]: f["severity"] for f in out["findings"]}
    assert severity["ns-026"] == "high"  # last updated 2023-04-10, > 730 days
    assert severity["ns-012"] == "high"  # 2024-11-03 = 739 days
    assert severity["ns-033"] == "medium"  # 2025-07-15 = 485 days


@pytest.mark.parametrize("days", [0, 29, 3651, -1])
def test_find_outdated_rejects_out_of_range_days(run_tool: RunTool, days: int) -> None:
    assert (
        run_tool("find_outdated_content", {"days_old": days}).status is ToolStatus.INVALID_ARGUMENTS
    )


# ---- find_duplicate_titles --------------------------------------------------


def test_find_duplicate_titles(run_tool: RunTool) -> None:
    out = run_tool("find_duplicate_titles", {}).output
    assert out is not None
    groups = [set(g["content_ids"]) for g in out["groups"]]
    assert sorted(groups, key=sorted) == sorted(m.DUPLICATE_TITLE_GROUPS, key=sorted)
    assert {f["content_id"] for f in out["findings"]} == set().union(*m.DUPLICATE_TITLE_GROUPS)
    finding = next(f for f in out["findings"] if f["content_id"] == "ns-020")
    assert finding["excerpt"] == "Tips for First-Time Home Buyers"
    assert "ns-023" in finding["reason"]


def test_find_duplicate_titles_rejects_arguments_it_does_not_accept(run_tool: RunTool) -> None:
    assert (
        run_tool("find_duplicate_titles", {"threshold": 0.8}).status is ToolStatus.INVALID_ARGUMENTS
    )


# ---- check_metadata ---------------------------------------------------------


def test_check_metadata_matches_manifest(run_tool: RunTool) -> None:
    out = run_tool("check_metadata", {"limit": 100}).output
    assert out is not None

    def ids(issue: str) -> set[str]:
        return {f["content_id"] for f in out["findings"] if f["issue"] == issue}

    assert ids("missing_meta_description") == m.MISSING_META_DESCRIPTION_IDS
    assert ids("meta_description_too_long") == m.LONG_META_DESCRIPTION_IDS
    assert ids("missing_meta_title") == m.MISSING_META_TITLE_IDS
    assert ids("meta_title_too_long") == m.LONG_META_TITLE_IDS
    assert out["counts"] == {
        "meta_description_too_long": 2,
        "meta_title_too_long": 3,
        "missing_meta_description": 5,
        "missing_meta_title": 1,
    }
    long_title = next(f for f in out["findings"] if f["content_id"] == "ns-011")
    assert "74 characters" in long_title["reason"]


def test_check_metadata_filters_and_cap(run_tool: RunTool) -> None:
    landing = run_tool("check_metadata", {"category": "landing"}).output
    assert landing is not None
    assert {f["content_id"] for f in landing["findings"]} == {"ns-037", "ns-040"}

    capped = run_tool("check_metadata", {"limit": 3}).output
    assert capped is not None
    assert len(capped["findings"]) == 3 and capped["truncated"] and capped["total_found"] == 11


# ---- check_internal_links ---------------------------------------------------


def test_check_internal_links_matches_manifest(run_tool: RunTool) -> None:
    out = run_tool("check_internal_links", {}).output
    assert out is not None
    assert out["pages_checked"] == m.TOTAL_ENTRIES
    assert out["links_checked"] > 40
    found = {
        (f["content_id"], href)
        for f in out["findings"]
        for (cid, href) in m.BROKEN_LINKS
        if f["content_id"] == cid and href in f["excerpt"]
    }
    assert found == m.BROKEN_LINKS
    assert len(out["findings"]) == len(m.BROKEN_LINKS)
    assert all(f["issue"] == "broken_internal_link" for f in out["findings"])


def test_check_internal_links_single_page(run_tool: RunTool) -> None:
    ok = run_tool("check_internal_links", {"content_id": "ns-001"}).output
    assert ok is not None and ok["pages_checked"] == 1 and ok["findings"] == []

    broken = run_tool("check_internal_links", {"content_id": "ns-034"}).output
    assert broken is not None and len(broken["findings"]) == 1

    missing = run_tool("check_internal_links", {"content_id": "ns-999"})
    assert missing.status is ToolStatus.NOT_FOUND


def _custom_ctx(tmp_path: Path, entries: list[ContentEntry]) -> tuple[Any, ToolContext]:
    db = str(tmp_path / "custom.db")
    content = SQLiteContentRepository(db)
    content.init_schema()
    content.replace_all(entries)
    audit = AuditService(SQLiteActivityRepository(db))
    proposals = ProposalService(content, SQLiteProposalRepository(db), audit)
    ctx = ToolContext(
        content_repo=content,
        proposals=proposals,
        as_of=m.SEED_REFERENCE_DATE.date(),
        site_base_url="https://www.northstarliving.example",
    )
    return build_default_registry(audit), ctx


def _entry(id: str, slug: str, content: str, **kw: Any) -> ContentEntry:
    base: dict[str, Any] = {
        "id": id,
        "title": f"Page {id}",
        "slug": slug,
        "content": content,
        "category": "blog",
        "status": "published",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-06-01T00:00:00Z",
        "meta_title": "A title",
        "meta_description": "A description",
        "canonical_url": f"https://www.northstarliving.example/{slug}",
    }
    return ContentEntry.model_validate(base | kw)


def test_link_checker_link_forms_and_unpublished_targets(tmp_path: Path) -> None:
    body = (
        "See [archived](/old-page), [draft](https://www.northstarliving.example/draft-page/), "
        '<a href="/missing?ref=nav#top">html</a>, [ok](/target#section), '
        "[external](https://other.example/x), [protocol-relative](//cdn.example/y), "
        "and [mail](mailto:hi@example.com)."
    )
    registry, ctx = _custom_ctx(
        tmp_path,
        [
            _entry("p-1", "source", body),
            _entry("p-2", "old-page", "x", status="archived"),
            _entry("p-3", "draft-page", "x", status="draft"),
            _entry("p-4", "target", "x"),
        ],
    )
    out = registry.execute("check_internal_links", {"content_id": "p-1"}, ctx).output
    assert out is not None
    assert out["links_checked"] == 4
    issues = sorted((f["issue"], f["reason"].split("'")[1]) for f in out["findings"])
    assert issues == [
        ("broken_internal_link", "/missing?ref=nav#top"),
        ("link_to_unpublished_page", "/old-page"),
        ("link_to_unpublished_page", "https://www.northstarliving.example/draft-page/"),
    ]


def test_metadata_canonical_checks(tmp_path: Path) -> None:
    registry, ctx = _custom_ctx(
        tmp_path,
        [
            _entry("c-1", "a", "x", canonical_url=None),
            _entry("c-2", "b", "x", canonical_url="https://www.northstarliving.example/other"),
            _entry("c-3", "c", "x", meta_title="   ", meta_description=""),
        ],
    )
    out = registry.execute("check_metadata", {}, ctx).output
    assert out is not None
    assert {(f["content_id"], f["issue"]) for f in out["findings"]} == {
        ("c-1", "missing_canonical_url"),
        ("c-2", "canonical_url_mismatch"),
        ("c-3", "missing_meta_title"),
        ("c-3", "missing_meta_description"),
    }


def test_tools_on_empty_repository(tmp_path: Path) -> None:
    registry, ctx = _custom_ctx(tmp_path, [])
    for name in (
        "find_outdated_content",
        "find_duplicate_titles",
        "check_metadata",
        "check_internal_links",
    ):
        result = registry.execute(name, {}, ctx)
        assert result.status is ToolStatus.OK, name
        assert result.output is not None and result.output["findings"] == []
    assert registry.execute("search_content", {"query": "x"}, ctx).output["matches"] == []


# ---- excerpt helpers --------------------------------------------------------


def test_excerpt_helpers() -> None:
    text = "alpha beta gamma delta epsilon zeta eta theta"
    assert excerpt_around(text, 11, 16, radius=6) == "…beta gamma delta…"
    assert excerpt_around(text, 0, 5, radius=100) == text
    assert find_excerpt("Hello   NORTHSTAR\n classic plan", "northstar classic") == (
        "Hello NORTHSTAR classic plan"
    )
    assert find_excerpt("nothing here", "missing") is None
