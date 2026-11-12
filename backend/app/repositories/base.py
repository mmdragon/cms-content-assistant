"""Storage-agnostic content repository interface.

SQLiteContentRepository implements this today. A future Contentstack / Contentful /
Sitecore adapter can implement the same Protocol without changing tools or routes.
"""

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.models.content import Category, ContentEntry, ContentStatus

MAX_PAGE_SIZE = 100
MAX_QUERY_LENGTH = 200


class ContentSort(StrEnum):
    UPDATED_DESC = "updated_desc"
    UPDATED_ASC = "updated_asc"
    TITLE_ASC = "title_asc"


class ContentQuery(BaseModel):
    """Validated filter/search parameters for listing content."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    q: str | None = Field(default=None, max_length=MAX_QUERY_LENGTH)
    category: Category | None = None
    status: ContentStatus | None = None
    tag: str | None = Field(default=None, max_length=64)
    sort: ContentSort = ContentSort.UPDATED_DESC
    limit: int = Field(default=20, ge=1, le=MAX_PAGE_SIZE)
    offset: int = Field(default=0, ge=0)


class ContentPage(BaseModel):
    items: list[ContentEntry]
    total: int
    limit: int
    offset: int


class ContentRepository(Protocol):
    def list_content(self, query: ContentQuery) -> ContentPage: ...

    def get_content(self, content_id: str) -> ContentEntry | None: ...

    def get_by_slug(self, slug: str) -> ContentEntry | None: ...

    def all_content(self) -> Sequence[ContentEntry]:
        """Every entry, ordered by id. Used by audit tools that scan the whole site."""
        ...

    def count(self) -> int: ...
