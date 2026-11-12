from pathlib import Path

import pytest
from pydantic import ValidationError

from app.models.content import Category, ContentStatus
from app.repositories.base import ContentQuery, ContentSort
from app.repositories.sqlite import SQLiteContentRepository
from app.services.seeding import ensure_seeded
from tests import seed_manifest as m


def test_count_and_all_content(repo: SQLiteContentRepository) -> None:
    assert repo.count() == m.TOTAL_ENTRIES
    ids = [e.id for e in repo.all_content()]
    assert ids == sorted(ids)
    assert len(ids) == m.TOTAL_ENTRIES


def test_get_content_round_trips_all_fields(repo: SQLiteContentRepository) -> None:
    entry = repo.get_content("ns-001")
    assert entry is not None
    assert entry.title == "Cedar Ridge"
    assert entry.slug == "communities/cedar-ridge"
    assert entry.category is Category.COMMUNITY
    assert entry.tags == ["larkspur-valley", "trails", "single-story"]
    assert entry.updated_at.tzinfo is not None


def test_get_content_missing_returns_none(repo: SQLiteContentRepository) -> None:
    assert repo.get_content("ns-999") is None


def test_get_by_slug_tolerates_slashes(repo: SQLiteContentRepository) -> None:
    entry = repo.get_by_slug("/homes/the-aurora/")
    assert entry is not None and entry.id == "ns-009"
    assert repo.get_by_slug("homes/the-kestrel") is None


def test_list_default_sort_is_newest_first(repo: SQLiteContentRepository) -> None:
    page = repo.list_content(ContentQuery(limit=100))
    stamps = [e.updated_at for e in page.items]
    assert stamps == sorted(stamps, reverse=True)
    assert page.total == m.TOTAL_ENTRIES


def test_list_sort_by_title(repo: SQLiteContentRepository) -> None:
    page = repo.list_content(ContentQuery(sort=ContentSort.TITLE_ASC, limit=100))
    titles = [e.title.lower() for e in page.items]
    assert titles == sorted(titles)


def test_search_is_case_insensitive_and_matches_discontinued_term(
    repo: SQLiteContentRepository,
) -> None:
    page = repo.list_content(ContentQuery(q="northstar CLASSIC", limit=100))
    assert {e.id for e in page.items} == m.DISCONTINUED_TERM_IDS
    assert page.total == len(m.DISCONTINUED_TERM_IDS)


def test_search_matches_metadata_and_tags(repo: SQLiteContentRepository) -> None:
    # "kayak" only appears in River Bend's body; "splash pad" in Willow Creek's meta description.
    assert {e.id for e in repo.list_content(ContentQuery(q="kayak")).items} == {"ns-006"}
    assert "ns-002" in {e.id for e in repo.list_content(ContentQuery(q="splash pad")).items}
    # "three-car-garage" is a tag only.
    assert {e.id for e in repo.list_content(ContentQuery(q="three-car-garage")).items} == {"ns-012"}


@pytest.mark.parametrize("term", ["%", "_", "\\", "100%"])
def test_search_escapes_like_wildcards(repo: SQLiteContentRepository, term: str) -> None:
    assert repo.list_content(ContentQuery(q=term)).total == 0


def test_search_blank_query_returns_everything(repo: SQLiteContentRepository) -> None:
    assert repo.list_content(ContentQuery(q="   ")).total == m.TOTAL_ENTRIES


def test_search_no_results(repo: SQLiteContentRepository) -> None:
    page = repo.list_content(ContentQuery(q="zeppelin"))
    assert page.total == 0
    assert page.items == []


def test_filter_by_category_and_status(repo: SQLiteContentRepository) -> None:
    homes = repo.list_content(ContentQuery(category=Category.HOME, limit=100))
    assert homes.total == 10
    assert all(e.category is Category.HOME for e in homes.items)

    archived = repo.list_content(ContentQuery(status=ContentStatus.ARCHIVED))
    assert {e.id for e in archived.items} == m.ARCHIVED_IDS


def test_filter_by_tag_is_exact_and_case_insensitive(repo: SQLiteContentRepository) -> None:
    page = repo.list_content(ContentQuery(tag="WARRANTY", limit=100))
    assert {e.id for e in page.items} == {"ns-028", "ns-030", "ns-033", "ns-036"}
    # Partial tag names do not match.
    assert repo.list_content(ContentQuery(tag="warr")).total == 0


def test_filters_combine_with_search(repo: SQLiteContentRepository) -> None:
    page = repo.list_content(
        ContentQuery(q="Northstar Classic", category=Category.LANDING, limit=100)
    )
    assert {e.id for e in page.items} == {"ns-036", "ns-039"}


def test_pagination(repo: SQLiteContentRepository) -> None:
    first = repo.list_content(ContentQuery(limit=15, offset=0, sort=ContentSort.TITLE_ASC))
    second = repo.list_content(ContentQuery(limit=15, offset=15, sort=ContentSort.TITLE_ASC))
    third = repo.list_content(ContentQuery(limit=15, offset=30, sort=ContentSort.TITLE_ASC))

    ids = [e.id for page in (first, second, third) for e in page.items]
    assert len(ids) == len(set(ids)) == m.TOTAL_ENTRIES
    assert len(third.items) == 10
    assert repo.list_content(ContentQuery(offset=500)).items == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 0},
        {"limit": 101},
        {"offset": -1},
        {"q": "x" * 201},
        {"category": "press-release"},
        {"sort": "id; DROP TABLE content_entries"},
        {"unknown": "field"},
    ],
)
def test_query_validation_rejects_bad_input(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ContentQuery.model_validate(kwargs)


def test_ensure_seeded_is_idempotent(tmp_path: Path) -> None:
    repository = SQLiteContentRepository(tmp_path / "idem.db")
    assert ensure_seeded(repository) == m.TOTAL_ENTRIES
    assert ensure_seeded(repository) == 0
    assert repository.count() == m.TOTAL_ENTRIES
