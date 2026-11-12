import pytest
from fastapi.testclient import TestClient

from tests import seed_manifest as m


def test_list_returns_summaries(client: TestClient) -> None:
    response = client.get("/api/content")
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == m.TOTAL_ENTRIES
    assert body["limit"] == 20 and body["offset"] == 0
    assert len(body["items"]) == 20
    item = body["items"][0]
    assert set(item) == {
        "id",
        "title",
        "slug",
        "category",
        "status",
        "updated_at",
        "tags",
        "excerpt",
    }
    assert len(item["excerpt"]) <= 160


def test_list_search_and_filters(client: TestClient) -> None:
    body = client.get("/api/content", params={"q": "Northstar Classic", "limit": 100}).json()
    assert {i["id"] for i in body["items"]} == m.DISCONTINUED_TERM_IDS

    body = client.get("/api/content", params={"category": "faq", "status": "published"}).json()
    assert body["total"] == 6
    assert all(i["category"] == "faq" for i in body["items"])

    body = client.get("/api/content", params={"tag": "financing"}).json()
    assert {i["id"] for i in body["items"]} == {"ns-032", "ns-039"}


def test_list_sort_title(client: TestClient) -> None:
    body = client.get("/api/content", params={"sort": "title_asc", "limit": 3}).json()
    assert [i["title"] for i in body["items"]] == [
        "5 Reasons Homeowners Love the Northstar Classic Plan",
        "About Northstar Living",
        "Aspen Grove",
    ]


def test_list_empty_result(client: TestClient) -> None:
    body = client.get("/api/content", params={"q": "zeppelin"}).json()
    assert body == {"items": [], "total": 0, "limit": 20, "offset": 0}


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 1000},
        {"offset": -5},
        {"category": "press-release"},
        {"status": "deleted"},
        {"sort": "random"},
        {"q": "x" * 201},
        {"unexpected": "1"},
    ],
)
def test_list_rejects_invalid_params(client: TestClient, params: dict[str, str | int]) -> None:
    assert client.get("/api/content", params=params).status_code == 422


def test_get_content_detail(client: TestClient) -> None:
    response = client.get("/api/content/ns-021")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "ns-021"
    assert "Northstar Classic" in body["content"]
    assert body["meta_description"]
    assert body["canonical_url"].endswith("/blog/why-homeowners-love-northstar-classic")


def test_get_content_preserves_missing_metadata(client: TestClient) -> None:
    body = client.get("/api/content/ns-008").json()
    assert body["meta_description"] is None


def test_get_content_not_found(client: TestClient) -> None:
    response = client.get("/api/content/ns-999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Content 'ns-999' not found"


@pytest.mark.parametrize("bad_id", ["NS-001", "ns_001", "-ns", "a" * 65, "ns-001%20OR%201=1"])
def test_get_content_rejects_malformed_id(client: TestClient, bad_id: str) -> None:
    assert client.get(f"/api/content/{bad_id}").status_code == 422
