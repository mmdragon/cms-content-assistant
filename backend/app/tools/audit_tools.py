"""Read-only audit tools that scan the whole site and return evidence-backed findings."""

import re
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta

from pydantic import BaseModel, Field

from app.errors import NotFoundError
from app.models.content import CONTENT_ID_PATTERN, Category, ContentEntry, ContentStatus
from app.tools.base import Tool, ToolContext, ToolInput, ToolKind
from app.tools.findings import Finding, Severity, excerpt_around, normalize_ws, truncate

META_TITLE_MAX = 60
META_DESCRIPTION_MAX = 160


def _filtered(
    ctx: ToolContext, category: Category | None, status: ContentStatus | None
) -> Sequence[ContentEntry]:
    return [
        e
        for e in ctx.content_repo.all_content()
        if (category is None or e.category == category) and (status is None or e.status == status)
    ]


class AuditOutput(BaseModel):
    total_found: int
    truncated: bool
    findings: list[Finding]


def _cap(findings: list[Finding], limit: int) -> tuple[list[Finding], int, bool]:
    return findings[:limit], len(findings), len(findings) > limit


# ---- find_outdated_content ------------------------------------------------


class FindOutdatedInput(ToolInput):
    days_old: int = Field(
        default=540, ge=30, le=3650, description="Flag pages not updated in this many days."
    )
    category: Category | None = None
    status: ContentStatus | None = None
    limit: int = Field(default=25, ge=1, le=50)


class FindOutdatedOutput(AuditOutput):
    as_of: date
    cutoff: date


def find_outdated_content(ctx: ToolContext, args: FindOutdatedInput) -> FindOutdatedOutput:
    cutoff = ctx.as_of - timedelta(days=args.days_old)
    stale = sorted(
        (e for e in _filtered(ctx, args.category, args.status) if e.updated_at.date() < cutoff),
        key=lambda e: (e.updated_at, e.id),
    )
    findings = []
    for e in stale:
        age = (ctx.as_of - e.updated_at.date()).days
        severity: Severity = "high" if age >= 2 * args.days_old else "medium"
        findings.append(
            Finding(
                content_id=e.id,
                title=e.title,
                issue="stale_content",
                field="updated_at",
                excerpt=f"Last updated {e.updated_at.date().isoformat()} ({age} days before "
                f"{ctx.as_of.isoformat()}); status: {e.status.value}",
                reason=f"Not updated in {age} days (threshold {args.days_old}).",
                recommendation="Review for accuracy; update, or archive if no longer relevant.",
                severity=severity,
            )
        )
    capped, total, truncated = _cap(findings, args.limit)
    return FindOutdatedOutput(
        as_of=ctx.as_of, cutoff=cutoff, total_found=total, truncated=truncated, findings=capped
    )


FIND_OUTDATED_CONTENT = Tool(
    name="find_outdated_content",
    description="List pages whose updated_at is older than `days_old` days, oldest first.",
    kind=ToolKind.READ,
    input_model=FindOutdatedInput,
    output_model=FindOutdatedOutput,
    handler=find_outdated_content,
)


# ---- find_duplicate_titles ------------------------------------------------


class FindDuplicateTitlesInput(ToolInput):
    status: ContentStatus | None = None


class DuplicateGroup(BaseModel):
    title: str
    content_ids: list[str]


class FindDuplicateTitlesOutput(AuditOutput):
    groups: list[DuplicateGroup]


def _title_key(title: str) -> str:
    return normalize_ws(title).casefold()


def find_duplicate_titles(
    ctx: ToolContext, args: FindDuplicateTitlesInput
) -> FindDuplicateTitlesOutput:
    by_key: dict[str, list[ContentEntry]] = defaultdict(list)
    for e in _filtered(ctx, None, args.status):
        by_key[_title_key(e.title)].append(e)

    groups: list[DuplicateGroup] = []
    findings: list[Finding] = []
    for entries in sorted(
        (v for v in by_key.values() if len(v) > 1), key=lambda v: _title_key(v[0].title)
    ):
        ids = [e.id for e in entries]
        groups.append(DuplicateGroup(title=entries[0].title, content_ids=ids))
        for e in entries:
            others = ", ".join(i for i in ids if i != e.id)
            findings.append(
                Finding(
                    content_id=e.id,
                    title=e.title,
                    issue="duplicate_title",
                    field="title",
                    excerpt=e.title,
                    reason=f"Same title as {others}.",
                    recommendation="Give each page a distinct title, or merge/redirect the "
                    "older page if they cover the same topic.",
                    severity="medium",
                )
            )
    return FindDuplicateTitlesOutput(
        total_found=len(findings), truncated=False, findings=findings, groups=groups
    )


FIND_DUPLICATE_TITLES = Tool(
    name="find_duplicate_titles",
    description="Group pages that share the same title (case- and whitespace-insensitive).",
    kind=ToolKind.READ,
    input_model=FindDuplicateTitlesInput,
    output_model=FindDuplicateTitlesOutput,
    handler=find_duplicate_titles,
)


# ---- check_metadata -------------------------------------------------------


class CheckMetadataInput(ToolInput):
    category: Category | None = None
    status: ContentStatus | None = None
    limit: int = Field(default=50, ge=1, le=100)


class CheckMetadataOutput(AuditOutput):
    counts: dict[str, int]


def _metadata_findings(e: ContentEntry) -> list[Finding]:
    out: list[Finding] = []

    def add(issue: str, field: str, excerpt: str, reason: str, rec: str, sev: Severity) -> None:
        out.append(
            Finding(
                content_id=e.id,
                title=e.title,
                issue=issue,
                field=field,
                excerpt=excerpt,
                reason=reason,
                recommendation=rec,
                severity=sev,
            )
        )

    title = (e.meta_title or "").strip()
    if not title:
        add(
            "missing_meta_title",
            "meta_title",
            "(empty)",
            "Meta title is missing.",
            f"Add a meta title of at most {META_TITLE_MAX} characters.",
            "high",
        )
    elif len(title) > META_TITLE_MAX:
        add(
            "meta_title_too_long",
            "meta_title",
            truncate(title),
            f"Meta title is {len(title)} characters (limit {META_TITLE_MAX}); "
            "search results may cut it off.",
            f"Shorten to {META_TITLE_MAX} characters or fewer.",
            "medium",
        )

    desc = (e.meta_description or "").strip()
    if not desc:
        add(
            "missing_meta_description",
            "meta_description",
            "(empty)",
            "Meta description is missing.",
            f"Add a meta description of at most {META_DESCRIPTION_MAX} characters.",
            "high",
        )
    elif len(desc) > META_DESCRIPTION_MAX:
        add(
            "meta_description_too_long",
            "meta_description",
            truncate(desc),
            f"Meta description is {len(desc)} characters (limit {META_DESCRIPTION_MAX}).",
            f"Shorten to {META_DESCRIPTION_MAX} characters or fewer.",
            "medium",
        )

    canonical = (e.canonical_url or "").strip()
    if not canonical:
        add(
            "missing_canonical_url",
            "canonical_url",
            "(empty)",
            "Canonical URL is missing.",
            "Set the canonical URL to this page's own URL.",
            "medium",
        )
    elif not canonical.rstrip("/").endswith("/" + e.slug):
        add(
            "canonical_url_mismatch",
            "canonical_url",
            canonical,
            f"Canonical URL does not point at this page's slug '{e.slug}'.",
            "Point the canonical URL at this page, unless it intentionally defers to another.",
            "medium",
        )
    return out


def check_metadata(ctx: ToolContext, args: CheckMetadataInput) -> CheckMetadataOutput:
    findings = [
        f for e in _filtered(ctx, args.category, args.status) for f in _metadata_findings(e)
    ]
    counts: dict[str, int] = defaultdict(int)
    for f in findings:
        counts[f.issue] += 1
    capped, total, truncated = _cap(findings, args.limit)
    return CheckMetadataOutput(
        total_found=total, truncated=truncated, findings=capped, counts=dict(sorted(counts.items()))
    )


CHECK_METADATA = Tool(
    name="check_metadata",
    description=(
        f"Check meta titles (missing or > {META_TITLE_MAX} chars), meta descriptions "
        f"(missing or > {META_DESCRIPTION_MAX} chars), and canonical URLs."
    ),
    kind=ToolKind.READ,
    input_model=CheckMetadataInput,
    output_model=CheckMetadataOutput,
    handler=check_metadata,
)


# ---- check_internal_links -------------------------------------------------

_MD_LINK = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)")
_HTML_LINK = re.compile(r"""href\s*=\s*["']([^"']+)["']""", re.I)


class CheckInternalLinksInput(ToolInput):
    content_id: str | None = Field(default=None, pattern=CONTENT_ID_PATTERN)
    limit: int = Field(default=50, ge=1, le=100)


class CheckInternalLinksOutput(AuditOutput):
    pages_checked: int
    links_checked: int


def _internal_path(href: str, site_base_url: str) -> str | None:
    """Return the normalized slug for an internal link, or None for external links."""
    base = site_base_url.rstrip("/")
    if href.startswith(base + "/") or href == base:
        href = href[len(base) :] or "/"
    if not href.startswith("/") or href.startswith("//"):
        return None
    path = href.split("#", 1)[0].split("?", 1)[0]
    return path.strip("/")


def check_internal_links(
    ctx: ToolContext, args: CheckInternalLinksInput
) -> CheckInternalLinksOutput:
    all_entries = ctx.content_repo.all_content()
    by_slug = {e.slug: e for e in all_entries}
    pages = [e for e in all_entries if args.content_id is None or e.id == args.content_id]
    if args.content_id is not None and not pages:
        raise NotFoundError(f"Unable to verify: no content with id '{args.content_id}'.")

    findings: list[Finding] = []
    links_checked = 0
    for e in pages:
        text = normalize_ws(e.content)
        for match in [*_MD_LINK.finditer(text), *_HTML_LINK.finditer(text)]:
            href = match.group(1)
            slug = _internal_path(href, ctx.site_base_url)
            if slug is None:
                continue
            links_checked += 1
            target = by_slug.get(slug)
            excerpt = excerpt_around(text, match.start(), match.end(), radius=60)
            if target is None:
                findings.append(
                    Finding(
                        content_id=e.id,
                        title=e.title,
                        issue="broken_internal_link",
                        field="content",
                        excerpt=excerpt,
                        reason=f"Links to '{href}', but no page has slug '{slug}'.",
                        recommendation="Point the link at an existing page or remove it.",
                        severity="high",
                    )
                )
            elif target.status != ContentStatus.PUBLISHED:
                findings.append(
                    Finding(
                        content_id=e.id,
                        title=e.title,
                        issue="link_to_unpublished_page",
                        field="content",
                        excerpt=excerpt,
                        reason=f"Links to '{href}' ({target.id}), which is {target.status.value}.",
                        recommendation="Link to a published page instead.",
                        severity="medium",
                    )
                )
    capped, total, truncated = _cap(findings, args.limit)
    return CheckInternalLinksOutput(
        total_found=total,
        truncated=truncated,
        findings=capped,
        pages_checked=len(pages),
        links_checked=links_checked,
    )


CHECK_INTERNAL_LINKS = Tool(
    name="check_internal_links",
    description=(
        "Check internal links (relative or on the site's own domain) in page bodies. Flags links "
        "to slugs that don't exist and links to draft/archived pages. External links are skipped."
    ),
    kind=ToolKind.READ,
    input_model=CheckInternalLinksInput,
    output_model=CheckInternalLinksOutput,
    handler=check_internal_links,
)
