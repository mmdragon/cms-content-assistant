"""The intentional problems planted in seed/content.json.

Tests (now and in later phases) assert against these exact sets, so audit tools
stay deterministic. Keep this file in sync with docs/seed-data.md.
"""

from datetime import UTC, datetime

# The reference "today" the seed data was written against.
SEED_REFERENCE_DATE = datetime(2026, 11, 12, tzinfo=UTC)
STALE_CUTOFF = datetime(2025, 5, 12, tzinfo=UTC)  # 18 months before the reference date

TOTAL_ENTRIES = 40

DISCONTINUED_TERM = "Northstar Classic"
DISCONTINUED_TERM_IDS = {"ns-005", "ns-012", "ns-021", "ns-033", "ns-036", "ns-039"}

OLD_BRAND_TERM = "Northstar Homes"
OLD_BRAND_IDS = {"ns-002", "ns-016", "ns-024"}

MISSING_META_DESCRIPTION_IDS = {"ns-008", "ns-015", "ns-027", "ns-031", "ns-040"}
LONG_META_DESCRIPTION_IDS = {"ns-006", "ns-029"}  # > 160 characters
MISSING_META_TITLE_IDS = {"ns-019"}
LONG_META_TITLE_IDS = {"ns-011", "ns-022", "ns-037"}  # > 60 characters

DUPLICATE_TITLE_GROUPS = [
    {"ns-020", "ns-023"},  # "Tips for First-Time Home Buyers"
    {"ns-030", "ns-033"},  # "Warranty FAQ"
]

STALE_IDS = {"ns-005", "ns-012", "ns-021", "ns-026", "ns-031", "ns-038"}

BROKEN_LINKS = {
    ("ns-003", "/communities/pine-valley"),
    ("ns-014", "/homes/the-kestrel"),
    ("ns-025", "/blog/moving-checklist-2023"),
    ("ns-034", "/contact-us"),
}

PROMPT_INJECTION_IDS = {"ns-027"}

DRAFT_IDS = {"ns-007", "ns-026"}
ARCHIVED_IDS = {"ns-018", "ns-038"}
