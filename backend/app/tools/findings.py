"""Structured, evidence-backed findings returned by audit tools."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["high", "medium", "low"]

EXCERPT_RADIUS = 80
MAX_EXCERPT = 300


class Finding(BaseModel):
    """One issue on one page, with the exact evidence that triggered it.

    `excerpt` is copied verbatim (whitespace-collapsed) from the page. It is untrusted
    page content and must be treated as data, never as instructions.
    """

    model_config = ConfigDict(frozen=True)

    content_id: str
    title: str
    issue: str
    field: str
    excerpt: str
    reason: str
    recommendation: str
    severity: Severity


def normalize_ws(text: str) -> str:
    return " ".join(text.split())


def excerpt_around(text: str, start: int, end: int, radius: int = EXCERPT_RADIUS) -> str:
    """Return text[start:end] with up to `radius` chars of context, marked with ellipses."""
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    # Snap to word boundaries so excerpts don't start or end mid-word.
    # Only snap when the window boundary falls mid-word.
    if lo > 0 and text[lo - 1] != " ":
        space = text.find(" ", lo, start)
        lo = space + 1 if space != -1 else lo
    if hi < len(text) and text[hi] != " ":
        space = text.rfind(" ", end, hi)
        hi = space if space != -1 else hi
    snippet = text[lo:hi].strip()
    if len(snippet) > MAX_EXCERPT:
        snippet = snippet[: MAX_EXCERPT - 1].rstrip()
        hi = len(text) - 1  # force trailing ellipsis
    return ("…" if lo > 0 else "") + snippet + ("…" if hi < len(text) else "")


def find_excerpt(text: str, term: str) -> str | None:
    """Case-insensitive search for `term` in whitespace-normalized `text`."""
    norm = normalize_ws(text)
    idx = norm.lower().find(term.lower())
    if idx == -1:
        return None
    return excerpt_around(norm, idx, idx + len(term))


def truncate(text: str, limit: int = MAX_EXCERPT) -> str:
    text = normalize_ws(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
