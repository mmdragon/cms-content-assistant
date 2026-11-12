"""Domain models for CMS content entries."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

# Content ids are opaque, URL-safe strings (seed data uses "ns-001" style ids).
CONTENT_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"
# Slugs: lowercase path segments, no leading/trailing slash, e.g. "communities/cedar-ridge".
SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*$"


class Category(StrEnum):
    COMMUNITY = "community"
    HOME = "home"
    BLOG = "blog"
    FAQ = "faq"
    LANDING = "landing"


class ContentStatus(StrEnum):
    PUBLISHED = "published"
    DRAFT = "draft"
    ARCHIVED = "archived"


def _require_tz(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return value


AwareDatetime = Annotated[datetime, AfterValidator(_require_tz)]


class ContentEntry(BaseModel):
    """A single page in the content repository."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=CONTENT_ID_PATTERN)
    title: str = Field(min_length=1, max_length=300)
    slug: str = Field(pattern=SLUG_PATTERN, max_length=200)
    content: str
    category: Category
    status: ContentStatus
    created_at: AwareDatetime
    updated_at: AwareDatetime
    # Metadata fields are optional on purpose: missing metadata is one of the
    # problems the assistant is meant to find, so the model must allow it.
    meta_title: str | None = None
    meta_description: str | None = None
    canonical_url: str | None = None
    tags: list[str] = Field(default_factory=list)


class ContentSummary(BaseModel):
    """Lightweight view of an entry for list/search results."""

    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    slug: str
    category: Category
    status: ContentStatus
    updated_at: datetime
    tags: list[str]
    excerpt: str

    @classmethod
    def from_entry(cls, entry: ContentEntry, excerpt_chars: int = 160) -> "ContentSummary":
        text = " ".join(entry.content.split())
        excerpt = text if len(text) <= excerpt_chars else text[: excerpt_chars - 1].rstrip() + "…"
        return cls(
            id=entry.id,
            title=entry.title,
            slug=entry.slug,
            category=entry.category,
            status=entry.status,
            updated_at=entry.updated_at,
            tags=list(entry.tags),
            excerpt=excerpt,
        )
