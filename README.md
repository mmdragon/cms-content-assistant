# CMS Content Assistant

A local-first, portfolio-quality web app that helps a content editor search a simulated headless CMS,
find stale or problematic pages, and review AI-proposed edits. **The assistant never changes content
without explicit human approval.**

> Status: **Phase 3 — deterministic tools.** 40 seeded pages, six read-only audit tools, a
> pending-only proposal tool, human approve/reject endpoints, and an activity log. The UI and
> the mock agent arrive in later phases (see [docs/BUILD_PROMPTS.md](docs/BUILD_PROMPTS.md)).

## Architecture

```
Browser ──► Next.js (frontend, :3000) ──/api/* proxy──► FastAPI (backend, :8000) ──► agent ──► allowlisted tools ──► SQLite
```

- The browser only talks to the Next.js server. `/api/*` is rewritten to the backend
  (`frontend/next.config.ts`), so the backend URL and any future model keys stay server-side.
- Backend layout follows [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): `api/` (routes only),
  `agents/`, `tools/`, `services/`, `repositories/`, `models/`, `schemas/`.
- All storage goes through the `ContentRepository` protocol (`backend/app/repositories/base.py`).
  `SQLiteContentRepository` implements it today; a Contentstack/Contentful/Sitecore adapter can
  implement the same interface later without touching routes or tools.

### Agent tools and the human-approval boundary

The agent can only act through an allowlisted `ToolRegistry` (`backend/app/tools/`):

| Tool | Kind | What it returns |
|---|---|---|
| `search_content(query, category?, status?, limit?)` | read | Matching pages, matched fields, excerpt |
| `get_content_by_id(content_id)` | read | Full page (body capped at 6,000 chars) |
| `find_outdated_content(days_old=540, category?, status?, limit?)` | read | Findings for pages not updated since the cutoff |
| `find_duplicate_titles(status?)` | read | Groups of pages sharing a title + findings |
| `check_metadata(category?, status?, limit?)` | read | Missing/long meta titles & descriptions, canonical URL problems |
| `check_internal_links(content_id?, limit?)` | read | Links to missing slugs and to draft/archived pages |
| `create_edit_proposal(content_id, field_name, proposed_value, rationale, evidence_excerpt)` | propose | A **pending** proposal id |

Every audit finding has the same shape: `content_id`, `title`, `issue`, `field`, `excerpt`
(verbatim page text), `reason`, `recommendation`, `severity`.

Guarantees, each covered by tests:

- **Allowlist + strict arguments.** Unknown tools and unknown/invalid arguments are rejected with
  a typed status; nothing is coerced silently.
- **Bounded.** Each call has a timeout (default 5 s), result caps (`limit`, `truncated`), and a
  64 KB output limit.
- **No fabricated evidence.** `create_edit_proposal` rejects an `evidence_excerpt` that does not
  appear in the page's current field. Missing pages return "Unable to verify".
- **Pending only.** Proposals can change only `title`, `content`, `meta_title`, or
  `meta_description`. There is no tool to approve, apply, update, or delete anything.
- **Human approval is the only write path.** `POST /api/proposals/{id}/approve` applies the
  change in one transaction, and only if the field still equals the value the proposal was drafted
  against (otherwise 409, nothing is overwritten).
- **Audited.** Every tool call, proposal, approval, and rejection is logged with actor, status,
  and arguments; secret-looking keys/values are redacted and long values truncated.
- **Page text is data.** Seed page `ns-027` contains a prompt-injection attempt; tests confirm it
  is returned as plain content and cannot cause any write.

```
cms-content-assistant/
  backend/     FastAPI + Pydantic, managed with uv
  frontend/    Next.js 16 + React 19 + TypeScript + Tailwind 4
  docs/        Brief, architecture, build prompts
  .env.example
```

## Prerequisites

- **Node.js 20.9+** (developed on 22 LTS)
- **[uv](https://docs.astral.sh/uv/)** — installs Python 3.12 for you (`uv python install 3.12`)

No API keys, paid services, or CMS accounts are needed.

## Setup

```bash
cp .env.example .env
```

```bash
cd backend && uv sync
```

```bash
cd frontend && npm install
```

## Run (two terminals)

```bash
cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend && npm run dev
```

Open http://localhost:3000 — the **Backend status** card should show "Healthy".
The API is also browsable at http://127.0.0.1:8000/docs.

On first start the backend creates `backend/data/cms.db` and loads the seed data. To reset the
database to the seed (deletes proposals and activity too):

```bash
cd backend && uv run python -m app.seed_db
```

See [docs/seed-data.md](docs/seed-data.md) for the dataset and the problems planted in it.

## Checks

Backend:

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Frontend:

```bash
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `CMS_ENVIRONMENT` | backend | `development` | Reported by `/api/health` |
| `CMS_DATABASE_PATH` | backend | `data/cms.db` | SQLite file (from Phase 2) |
| `CMS_CORS_ORIGINS` | backend | `http://localhost:3000,...` | Browser origins allowed to call the API directly |
| `CMS_AGENT_PROVIDER` | backend | `mock` | Demo mode; no key needed |
| `CMS_AUDIT_REFERENCE_DATE` | backend | today | "Today" for staleness audits. `.env.example` pins `2026-11-12` so demo results match the seed |
| `CMS_SITE_BASE_URL` | backend | `https://www.northstarliving.example` | Absolute links on this origin count as internal |
| `CMS_TOOL_TIMEOUT_SECONDS` | backend | `5` | Per-tool-call timeout |
| `BACKEND_URL` | frontend (`frontend/.env.local`) | `http://127.0.0.1:8000` | Proxy target for `/api/*` |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness + app version, environment, agent provider |
| GET | `/api/content` | List/search content. Query params: `q`, `category`, `status`, `tag`, `sort` (`updated_desc` \| `updated_asc` \| `title_asc`), `limit` (1–100, default 20), `offset`. Unknown params → 422 |
| GET | `/api/content/{id}` | Full entry, or 404 |
| GET | `/api/proposals` | List proposals (`status`, `content_id`, `limit`, `offset`), newest first |
| GET | `/api/proposals/{id}` | One proposal with original and proposed values, rationale, evidence |
| POST | `/api/proposals/{id}/approve` | Apply a pending proposal. Optional body `{"note": "..."}`. 409 if not pending or the page changed since |
| POST | `/api/proposals/{id}/reject` | Reject a pending proposal. Optional body `{"note": "..."}` |
| GET | `/api/activity` | Activity log (`event_type`, `limit`, `offset`), newest first |
| GET | `/api/tools` | The agent's tool allowlist with JSON schemas |

Search is a case-insensitive substring match over title, body, meta title, meta description, and
tags. `%` and `_` are matched literally. Approve and reject are the only non-GET endpoints.

## Limitations (current phase)

- No agent or UI for tools/proposals yet; proposals are created through the tool registry
  (the mock agent in Phase 5 will call it).
- Search is substring-based (no stemming, ranking, or semantic search).
- No authentication (out of scope for the MVP; the backend binds to `127.0.0.1` only).
