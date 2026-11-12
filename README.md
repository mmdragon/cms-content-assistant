# CMS Content Assistant

A local-first, portfolio-quality web app that helps a content editor search a simulated headless CMS,
find stale or problematic pages, and review AI-proposed edits. **The assistant never changes content
without explicit human approval.**

> Status: **Phase 6 — optional Claude provider.** The assistant runs in free demo mode by default.
> It can optionally use Claude via the Anthropic API (paid, needs your own API key); see
> [docs/claude-provider.md](docs/claude-provider.md). Final review is next
> (see [docs/BUILD_PROMPTS.md](docs/BUILD_PROMPTS.md)).

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
  frontend/    Next.js 16 + React 19 + TypeScript + Tailwind 4 (Vitest + Testing Library)
  docs/        Brief, architecture, build prompts
  .env.example
```

## Prerequisites

- **Node.js 22+**
- **[uv](https://docs.astral.sh/uv/)** — installs Python 3.12 for you (`uv python install 3.12`)

No API keys, paid services, or CMS accounts are needed. The optional Claude provider needs an
Anthropic API key and is billed per token; it is off unless you turn it on.

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

Open http://localhost:3000. The header shows **Backend OK** when the API is reachable.
The API is also browsable at http://127.0.0.1:8000/docs.

On first start the backend creates `backend/data/cms.db` and loads the seed data. To reset the
database to the seed (deletes proposals and activity too):

```bash
cd backend && uv run python -m app.seed_db
```

See [docs/seed-data.md](docs/seed-data.md) for the dataset and the problems planted in it.

## Using the app

| Screen | What you can do |
|---|---|
| **Content** (`/`) | Search titles, body, metadata, and tags; filter by category and status; sort; paginate. Filters live in the URL, so views can be bookmarked or shared. |
| **Page detail** (`/content/{id}`) | Read the body (always rendered as plain text, never HTML), see metadata with length checks, and jump to proposals for the page. |
| **Proposals** (`/proposals`) | Pending / approved / rejected / all tabs. The header badge shows the pending count. |
| **Proposal review** (`/proposals/{id}`) | Side-by-side or inline word diff, the rationale, and the exact evidence quoted from the page. **Approve and apply** and **Reject** both open a confirmation dialog with an optional note. Approval is disabled if the page changed since the draft. |
| **Activity** (`/activity`) | Every tool call, proposal, approval, and rejection, filterable by type, with redacted details. |
| **Assistant** (header button) | Chat with the demo assistant. Side panel on desktop, full-screen on phones. History is kept for the browser session. |

All screens have loading, empty, and error states, work at phone width, support light and dark
mode, and are keyboard accessible (skip link, visible focus, labelled controls, native modal
dialogs, Esc closes the assistant panel).

## Demo mode and example prompts

The assistant runs on a **deterministic, rule-based mock agent** (`backend/app/agents/mock.py`).
No model or API key is involved, and the UI labels it as demo mode. It matches each message against a
fixed set of supported requests, calls the allowlisted tools, and builds its reply only from tool
output, so every finding cites a page id, field, and verbatim excerpt.

| Try | What happens |
|---|---|
| *Find pages that still mention the discontinued Northstar Classic plan. Suggest updated wording, but do not apply any changes.* | Lists the 6 pages (8 places) with excerpts and drafts 8 **pending** proposals swapping in “Northstar Care”. Notes that the ns-021 slug also contains the old name. Nothing is changed. |
| *Which pages still use the old brand name Northstar Homes?* | 3 pages, with excerpts. Add “suggest a fix” to draft proposals. |
| *Which pages have missing or overly long metadata?* | 11 issues across 11 pages, with counts per type. |
| *List pages not updated in the last 18 months.* | 6 pages, oldest first. Durations like “90 days” or “2 years” are understood. |
| *Are there duplicate titles?* | 2 groups (4 pages). |
| *Check for broken internal links.* | 4 links to slugs that don't exist. |
| *Tell me about ns-027* | Page summary and its issues, including a warning that the page contains a prompt-injection attempt, which the assistant ignores. |
| *Run a full audit* | All four checks at once. |
| *Which pages mention "splash pad"?* | Search for any quoted phrase. |
| *Approve all pending proposals* | Refused: only an editor can approve, from the Proposals screen. |

Anything else gets a short help message instead of a guess. The agent:

- drafts proposals only for name replacements it can make mechanically, and says that other details
  in those sentences still need checking. It won't invent meta descriptions or "freshen" stale pages;
- skips fields that already have a pending proposal, so repeating a request doesn't duplicate drafts;
- stops after 25 tool calls and 10 drafts per message (configurable), and says so;
- treats “do not apply” as a negation, not a write request.

## Checks

Backend:

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Frontend:

```bash
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

## Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `CMS_ENVIRONMENT` | backend | `development` | Reported by `/api/health` |
| `CMS_DATABASE_PATH` | backend | `data/cms.db` | SQLite file (from Phase 2) |
| `CMS_CORS_ORIGINS` | backend | `http://localhost:3000,...` | Browser origins allowed to call the API directly |
| `CMS_AGENT_PROVIDER` | backend | `mock` | `mock` = demo mode, no key. `claude` = Anthropic API (paid) |
| `CMS_AUDIT_REFERENCE_DATE` | backend | today | "Today" for staleness audits. `.env.example` pins `2026-11-12` so demo results match the seed |
| `CMS_SITE_BASE_URL` | backend | `https://www.northstarliving.example` | Absolute links on this origin count as internal |
| `CMS_TOOL_TIMEOUT_SECONDS` | backend | `5` | Per-tool-call timeout |
| `CMS_AGENT_MAX_TOOL_CALLS` | backend | `25` | Tool-call budget for one assistant turn |
| `CMS_AGENT_PROVIDER` = `claude` + `ANTHROPIC_API_KEY` | backend | off | Use Claude instead of the demo agent. Paid; see [docs/claude-provider.md](docs/claude-provider.md) for all `CMS_CLAUDE_*` settings |
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
| POST | `/api/assistant/chat` | One assistant turn. Body `{"messages": [{"role": "user" \| "assistant", "content": "..."}]}` (max 20 messages, 2,000 chars each, last must be `user`). Returns `message`, `findings`, `proposals` (pending drafts), `tool_calls`, `notes`, `demo_mode` |

Search is a case-insensitive substring match over title, body, meta title, meta description, and
tags. `%` and `_` are matched literally. Approve and reject are the only endpoints that change
content; the chat endpoint can at most create pending proposals.

## Limitations (current phase)

- The demo agent understands a fixed set of phrasings; it is a keyword router, not a language
  model. Only the latest message is interpreted (history is sent for a future model provider).
- It drafts only mechanical name replacements and does not verify facts beyond the content store.
- Page bodies are shown as plain text; Markdown is not rendered.
- Search is substring-based (no stemming, ranking, or semantic search).
- No authentication (out of scope for the MVP; the backend binds to `127.0.0.1` only).
