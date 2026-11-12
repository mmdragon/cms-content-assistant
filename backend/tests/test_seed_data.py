"""Guard the seed dataset: it must contain exactly the planted problems, and nothing else."""

import json
import re
from collections import defaultdict
from pathlib import Path

import pytest

from app.models.content import ContentEntry
from app.services.seeding import SEED_FILE, load_seed_entries
from tests import seed_manifest as m

LINK_RE = re.compile(r"\]\((/[^)\s]*)\)")


@pytest.fixture(scope="module")
def entries() -> list[ContentEntry]:
    return load_seed_entries()


def _text(e: ContentEntry) -> str:
    return " ".join(
        [e.title, e.content, e.meta_title or "", e.meta_description or "", " ".join(e.tags)]
    ).lower()


def test_entry_count_and_unique_keys(entries: list[ContentEntry]) -> None:
    assert len(entries) == m.TOTAL_ENTRIES >= 30
    assert len({e.id for e in entries}) == len(entries)
    assert len({e.slug for e in entries}) == len(entries)


def test_all_categories_present(entries: list[ContentEntry]) -> None:
    assert {e.category.value for e in entries} == {"community", "home", "blog", "faq", "landing"}


def test_timestamps_are_consistent(entries: list[ContentEntry]) -> None:
    for e in entries:
        assert e.created_at <= e.updated_at, e.id
        assert e.updated_at <= m.SEED_REFERENCE_DATE, e.id


def test_canonical_urls_use_reserved_example_domain(entries: list[ContentEntry]) -> None:
    for e in entries:
        assert e.canonical_url == f"https://www.northstarliving.example/{e.slug}"


def test_statuses(entries: list[ContentEntry]) -> None:
    assert {e.id for e in entries if e.status == "draft"} == m.DRAFT_IDS
    assert {e.id for e in entries if e.status == "archived"} == m.ARCHIVED_IDS


def test_discontinued_term_pages(entries: list[ContentEntry]) -> None:
    hits = {e.id for e in entries if m.DISCONTINUED_TERM.lower() in _text(e)}
    assert hits == m.DISCONTINUED_TERM_IDS


def test_old_brand_pages(entries: list[ContentEntry]) -> None:
    hits = {e.id for e in entries if m.OLD_BRAND_TERM.lower() in _text(e)}
    assert hits == m.OLD_BRAND_IDS


def test_metadata_problems(entries: list[ContentEntry]) -> None:
    assert {e.id for e in entries if not e.meta_description} == m.MISSING_META_DESCRIPTION_IDS
    assert {
        e.id for e in entries if e.meta_description and len(e.meta_description) > 160
    } == m.LONG_META_DESCRIPTION_IDS
    assert {e.id for e in entries if not e.meta_title} == m.MISSING_META_TITLE_IDS
    assert {
        e.id for e in entries if e.meta_title and len(e.meta_title) > 60
    } == m.LONG_META_TITLE_IDS


def test_duplicate_titles(entries: list[ContentEntry]) -> None:
    by_title: dict[str, set[str]] = defaultdict(set)
    for e in entries:
        by_title[e.title.strip().lower()].add(e.id)
    groups = [ids for ids in by_title.values() if len(ids) > 1]
    assert sorted(groups, key=sorted) == sorted(m.DUPLICATE_TITLE_GROUPS, key=sorted)


def test_stale_pages(entries: list[ContentEntry]) -> None:
    assert {e.id for e in entries if e.updated_at < m.STALE_CUTOFF} == m.STALE_IDS


def test_broken_internal_links(entries: list[ContentEntry]) -> None:
    slugs = {e.slug for e in entries}
    broken = {
        (e.id, link)
        for e in entries
        for link in LINK_RE.findall(e.content)
        if link.strip("/") not in slugs
    }
    assert broken == m.BROKEN_LINKS


def test_prompt_injection_fixture_present(entries: list[ContentEntry]) -> None:
    hits = {e.id for e in entries if "ignore all previous instructions" in e.content.lower()}
    assert hits == m.PROMPT_INJECTION_IDS


def test_load_rejects_duplicate_ids(tmp_path: Path) -> None:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    dup = dict(data[1], id=data[0]["id"])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([data[0], dup]), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate id"):
        load_seed_entries(bad)


def test_load_rejects_naive_timestamps(tmp_path: Path) -> None:
    data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([dict(data[0], updated_at="2026-01-01T00:00:00")]), encoding="utf-8")

    with pytest.raises(ValueError, match="timezone"):
        load_seed_entries(bad)
