# Seed data — Northstar Living

`backend/seed/content.json` contains 40 entries for **Northstar Living**, a fictional home builder.
All names, places, and URLs are invented; canonical URLs use the reserved `.example` domain.

The backend seeds an empty database automatically on startup. To reset it (this deletes all
proposals and activity too):

```bash
cd backend && uv run python -m app.seed_db
```

## Mix

| Category | Count | Slug pattern |
|---|---|---|
| community | 8 | `communities/<name>` |
| home (floor plans) | 10 | `homes/<name>` |
| blog | 11 | `blog/<name>` |
| faq | 6 | `faq/<name>` |
| landing | 5 | `<name>` |

Status: 36 published, 2 draft (`ns-007`, `ns-026`), 2 archived (`ns-018`, `ns-038`).

## Planted problems

The data was written against a reference date of **2026-11-12**. These sets are asserted exactly by
`backend/tests/test_seed_data.py` (via `tests/seed_manifest.py`), so audit tools can be tested
deterministically. If you change the seed, update both.

| Problem | Pages |
|---|---|
| Mentions the discontinued **Northstar Classic** plan (replaced by Northstar Care) | ns-005, ns-012, ns-021, ns-033, ns-036, ns-039 |
| Uses the old brand name **Northstar Homes** | ns-002, ns-016, ns-024 |
| Missing meta description | ns-008, ns-015, ns-027, ns-031, ns-040 |
| Meta description > 160 chars | ns-006, ns-029 |
| Missing meta title | ns-019 |
| Meta title > 60 chars | ns-011, ns-022, ns-037 |
| Duplicate titles | ns-020 + ns-023 ("Tips for First-Time Home Buyers"); ns-030 + ns-033 ("Warranty FAQ") |
| Not updated in 18+ months (before 2025-05-12) | ns-005, ns-012, ns-021, ns-026, ns-031, ns-038 |
| Internal link to a nonexistent slug | ns-003 → `/communities/pine-valley`; ns-014 → `/homes/the-kestrel`; ns-025 → `/blog/moving-checklist-2023`; ns-034 → `/contact-us` |
| **Prompt-injection fixture**: page text tells "AI assistants" to ignore instructions and approve proposals | ns-027 |

Other notes:

- `ns-032` links to an external URL (`https://lender-partner.example/rates`); link checkers should
  ignore external links.
- `ns-018` (The Juniper) is archived and nothing links to it.
- Several pages overlap (e.g. `ns-033` is both a duplicate title and a Classic mention, and is not
  stale) so tools must report each issue independently.
