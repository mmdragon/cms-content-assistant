# CMS Content Assistant

A local-first web app that helps a website content editor search a simulated headless CMS, find
stale or problematic pages, ask an assistant about them, and review AI-drafted edits as diffs.
**The assistant never changes content on its own: every edit is a pending draft until a human
approves it.**

- Runs entirely on your machine: FastAPI + SQLite backend, Next.js frontend.
- **Demo mode needs no API key and costs nothing.** A deterministic, rule-based agent answers a set
  of supported requests with evidence from the content store.
- Optional Claude provider (Anthropic API, paid, off by default) behind the same tools and guardrails.
- Seeded with 40 pages for **Northstar Living**, a fictional home builder, with problems planted on
  purpose: a discontinued plan name, an old brand name, missing or overlong metadata, duplicate
  titles, stale pages, broken internal links, and a prompt-injection attempt.

## Contents

- [Quick start](#quick-start)
- [Demo walkthrough](#demo-walkthrough)
- [Example prompts](#example-prompts)
- [Architecture](#architecture)
- [Safety and trust model](#safety-and-trust-model)
- [Testing and checks](#testing-and-checks)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Optional: Claude provider](#optional-claude-provider)
- [Screenshots](#screenshots)
- [Limitations](#limitations)
- [Future integrations](#future-integrations)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Quick start

**Prerequisites:** [Node.js](https://nodejs.org) 22 or newer, and [uv](https://docs.astral.sh/uv/)
(it installs Python 3.12 for you). No API keys, paid services, or CMS accounts are needed.

From the repository root:

```bash
cp .env.example .env
```

```bash
cd backend && uv sync
```

```bash
cd frontend && npm install
```

Then run the two servers in separate terminals:

```bash
cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
cd frontend && npm run dev
```

Open **http://localhost:3000**. The header shows **Backend OK** when the API is reachable. The
interactive API docs are at http://127.0.0.1:8000/docs.

On first start the backend creates `backend/data/cms.db` and loads the seed data. To reset
everything (content, proposals, activity) back to the seed:

```bash
cd backend && uv run python -m app.seed_db
```

## Demo walkthrough

A five-minute tour that covers the whole workflow:

1. **Browse.** On **Content**, search `Northstar Classic`, then filter Category to *Landing page*.
   Open *Home Warranty* (ns-036) to see the body, metadata length checks, and related proposals.
2. **Ask.** Click **Assistant** and choose the first example prompt:
   *“Find pages that still mention the discontinued Northstar Classic plan. Suggest updated
   wording, but do not apply any changes.”* The reply lists 6 pages (8 places), quotes each
   excerpt, notes that one URL also contains the old name, and drafts 8 pending proposals. The
   **Proposals** badge shows 8.
3. **Review.** Click **Review →** on a draft. Compare the before/after diff (side by side or
   inline), read the rationale and the quoted evidence, then **Approve and apply** (with an
   optional note) or **Reject**. Both ask for confirmation.
4. **Check the safety rails.** Ask *“Tell me about ns-027”*: the page contains text telling AI
   assistants to approve every proposal, and the assistant flags it instead of obeying. Ask
   *“Approve all pending proposals”*: it refuses and points you to the Proposals screen.
5. **Audit trail.** Open **Activity** to see every tool call, draft, approval, and rejection, with
   the note you entered and redacted details.

## Example prompts

The demo agent (`backend/app/agents/mock.py`) is a keyword router, not a language model. It
understands these requests and phrasings close to them; anything else gets a help message.

| Prompt | Result |
|---|---|
| *Find pages that still mention the discontinued Northstar Classic plan. Suggest updated wording, but do not apply any changes.* | 6 pages, 8 excerpts, 8 pending drafts replacing the name with “Northstar Care”. Nothing changes. |
| *Which pages still use the old brand name Northstar Homes?* | 3 pages with excerpts. Add “suggest a fix” to get drafts. |
| *Which pages have missing or overly long metadata?* | 11 issues across 11 pages, with counts per type. |
| *List pages not updated in the last 18 months.* | 6 pages, oldest first. “90 days” or “2 years” work too. |
| *Are there duplicate titles?* | 2 groups (4 pages). |
| *Check for broken internal links.* | 4 links to pages that don't exist. |
| *Tell me about ns-031* | Page summary and its issues. |
| *Run a full audit* | Stale pages, metadata, duplicates, and links together. |
| *Which pages mention "splash pad"?* | Search for any quoted phrase. |
| *Approve all pending proposals* | Refused; only an editor can approve. |

The demo agent only drafts mechanical name replacements and says that the surrounding details
still need checking. It won't invent meta descriptions or rewrite stale pages, because that would
mean making up facts. Repeating a request doesn't create duplicate drafts.

## Architecture

```
Browser ──► Next.js :3000 ──/api/* proxy──► FastAPI :8000
                                              ├─ routes (api/)            request/response only
                                              ├─ AgentService ─► provider (mock | claude)
                                              │                   └─ ToolRunner (per-turn budget)
                                              ├─ ToolRegistry (allowlist, validation, timeouts,
                                              │                output caps, audit logging)
                                              │    ├─ 6 read tools
                                              │    └─ create_edit_proposal ─► pending only
                                              ├─ ProposalService ─ approve/reject (human only)
                                              ├─ AuditService ─► activity_events
                                              └─ Repositories ─► SQLite (content, proposals, activity)
```

- The browser only talks to the Next.js server; `/api/*` is proxied to FastAPI
  (`frontend/next.config.ts`). The backend URL and any model credentials stay server-side.
- **Storage is behind an interface.** Routes and tools depend on the `ContentRepository` protocol
  (`backend/app/repositories/base.py`), not on SQLite. See
  [Future integrations](#future-integrations).
- **The agent is behind an interface too.** `AgentProvider` (`backend/app/agents/base.py`) has two
  implementations, the demo `MockAgent` and the optional `ClaudeAgent`. Both reach data only through
  the same `ToolRunner` → `ToolRegistry` path.

```
cms-content-assistant/
  backend/
    app/
      api/            FastAPI routes (content, proposals, activity, assistant, health)
      agents/         Agent contracts, mock agent, Claude agent, service
      tools/          Tool registry, read tools, proposal tool, finding model
      services/       Proposal lifecycle, audit logging, seeding
      repositories/   SQLite access (content, proposals, activity)
      models/ schemas/ Pydantic domain and response models
    seed/content.json 40 fictional pages
    tests/            pytest suite
  frontend/
    app/              Next.js routes (content, proposals, activity)
    components/       UI: library, detail, diff review, activity, assistant panel
    lib/ types/       API client, data hook, diff, formatting, shared types
  docs/               Brief, architecture, build prompts, seed data, Claude provider
```

**Agent tools** (`GET /api/tools` returns them with JSON schemas):

| Tool | Kind | Returns |
|---|---|---|
| `search_content(query, category?, status?, limit?)` | read | Matching pages, matched fields, excerpt |
| `get_content_by_id(content_id)` | read | Full page (body capped at 6,000 chars) |
| `find_outdated_content(days_old=540, category?, status?, limit?)` | read | Pages not updated since the cutoff |
| `find_duplicate_titles(status?)` | read | Groups of pages sharing a title |
| `check_metadata(category?, status?, limit?)` | read | Missing/long meta titles and descriptions, canonical URL problems |
| `check_internal_links(content_id?, limit?)` | read | Links to missing slugs, or to draft/archived pages |
| `create_edit_proposal(content_id, field_name, proposed_value, rationale, evidence_excerpt)` | propose | A **pending** proposal |

Every finding has the same shape: `content_id`, `title`, `issue`, `field`, `excerpt` (verbatim
page text), `reason`, `recommendation`, `severity`. (`docs/ARCHITECTURE.md` calls the metadata tool
`audit_metadata`; it is `check_metadata` here, matching the project brief.)

## Safety and trust model

Each point below is covered by tests.

| Requirement | How it's enforced |
|---|---|
| Content is untrusted data | Page text is only searched and quoted. The demo agent flags text addressed to AI assistants; the Claude agent receives tool output inside `<untrusted_tool_output>` tags with a system rule never to follow it. The UI renders page text as plain text, never HTML. Seed page ns-027 tests this. |
| Allowlisted tools, validated arguments | One registry with exactly 7 tools; unknown tools and unknown or invalid arguments are rejected with a typed status. |
| Read tools separate from write | Six read tools have no side effects. The only other tool creates **pending** proposals for 4 editable fields. No tool can approve, apply, or delete. |
| Approval required for every write | `POST /api/proposals/{id}/approve` is the only code path that changes content. It runs in one transaction with a compare-and-set: if the field changed since the draft, it returns 409 and overwrites nothing. The UI asks for confirmation. |
| No invented facts | Proposals must quote evidence that exists in the current field; findings shown in the UI come from tool output, not model prose; missing pages return “Unable to verify”. |
| Audit log | Every tool call (name, redacted arguments, status, duration, timestamp), draft, approval, rejection, and assistant error is recorded. Secret-looking keys and values are masked; long values are truncated. |
| Bounded execution | Per-tool timeout (5 s), result limits and a 64 KB output cap, 25 tool calls and 10 drafts per message, and at most 8 model round trips for Claude. |
| Secrets stay on the server | The Anthropic key is read from the backend environment by the SDK only; it is not a setting, not logged, and never sent to the browser. |

There is no authentication: production auth and multi-tenancy are non-goals for this MVP, and the
backend binds to `127.0.0.1`.

## Testing and checks

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy
```

```bash
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

- **Backend:** 209 pytest tests. They cover the seed data (asserting the exact set of planted
  problems from `tests/seed_manifest.py`), repository queries and SQL-injection-style input, every
  tool including invalid arguments, empty results, timeouts, and output limits, stale-content
  detection, the full approval workflow (approve, reject, double approve, page changed since the
  draft), the demo agent's routing and refusals, prompt injection, and the Claude provider against a
  scripted fake client (no network, no key).
- **Frontend:** 33 Vitest + Testing Library tests for the diff, API error handling, the approval
  dialog, and the assistant conversation.
- Strict mypy, Ruff, ESLint, and a production Next.js build.

Tests use a temporary database and ignore your `.env`, so they never touch your data or call a
paid API.

## Configuration

Copy `.env.example` to `.env` at the repository root; the backend reads it when started from
`backend/`. Every setting has a working default.

| Variable | Default | Purpose |
|---|---|---|
| `CMS_DATABASE_PATH` | `data/cms.db` | SQLite file (relative to `backend/`) |
| `CMS_AUDIT_REFERENCE_DATE` | today | “Today” for staleness checks. `.env.example` pins `2026-11-12` so demo results match the seed and the docs |
| `CMS_AGENT_PROVIDER` | `mock` | `mock` = demo mode, free. `claude` = Anthropic API, paid |
| `CMS_AGENT_MAX_TOOL_CALLS` | `25` | Tool calls allowed per assistant message |
| `CMS_TOOL_TIMEOUT_SECONDS` | `5` | Per-tool-call timeout |
| `CMS_SITE_BASE_URL` | `https://www.northstarliving.example` | Absolute links on this origin count as internal |
| `CMS_CORS_ORIGINS` | `http://localhost:3000,...` | Browser origins allowed to call the API directly |
| `CMS_ENVIRONMENT` | `development` | Reported by `/api/health` |
| `CMS_CLAUDE_*` | see [docs/claude-provider.md](docs/claude-provider.md) | Model, effort, loop limits, timeout, fallback |
| `BACKEND_URL` (in `frontend/.env.local`) | `http://127.0.0.1:8000` | Where Next.js proxies `/api/*` |

## API reference

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Status, version, environment, agent provider and model, `demo_mode` |
| GET | `/api/content` | List/search. Params: `q`, `category`, `status`, `tag`, `sort` (`updated_desc`, `updated_asc`, `title_asc`), `limit` (1–100), `offset`. Unknown params → 422 |
| GET | `/api/content/{id}` | One page, or 404 |
| GET | `/api/proposals` | Proposals, newest first. Params: `status`, `content_id`, `limit`, `offset` |
| GET | `/api/proposals/{id}` | One proposal: original and proposed values, rationale, evidence |
| POST | `/api/proposals/{id}/approve` | Apply a pending proposal. Optional body `{"note": "..."}`. 409 if not pending or the page changed |
| POST | `/api/proposals/{id}/reject` | Reject a pending proposal. Optional body `{"note": "..."}` |
| GET | `/api/activity` | Activity log, newest first. Params: `event_type`, `limit`, `offset` |
| GET | `/api/tools` | The agent's tool allowlist with JSON schemas |
| POST | `/api/assistant/chat` | One assistant turn. Body `{"messages": [{"role": "user" or "assistant", "content": "..."}]}` (max 20 messages of 2,000 chars, last from `user`). Returns `message`, `findings`, `proposals`, `tool_calls`, `notes`, `demo_mode`. 503 if the Claude provider is unavailable |

Approve and reject are the only endpoints that change content. The chat endpoint can at most
create pending proposals.

## Optional: Claude provider

Set `CMS_AGENT_PROVIDER=claude` and export `ANTHROPIC_API_KEY` in the backend's shell to have Claude
(default `claude-opus-5-5`) answer free-form questions using the same tools and guardrails. **This
uses the Anthropic API, which is billed per token to your API account; a Claude.ai subscription
doesn't cover it.** Read [docs/claude-provider.md](docs/claude-provider.md) for costs, setup, and
how it stays safe. It is tested with a fake client only; try it by hand after enabling.

## Screenshots

To capture screenshots for a portfolio or README:

1. Reset the data so counts match the docs: `cd backend && uv run python -m app.seed_db`.
2. Make sure `CMS_AUDIT_REFERENCE_DATE=2026-11-12` is set (it is in `.env.example`).
3. Use a 1440×900 browser window for desktop shots and 390×844 for mobile, in both light and dark
   mode if you want to show theming.
4. Capture, in this order (each builds on the previous step):
   - **Content library**: search `Northstar Classic`.
   - **Page detail**: ns-008 (shows the “Missing” meta description badge).
   - **Assistant**: panel open after the first example prompt, with the summary and the first
     findings visible.
   - **Proposal review**: the ns-036 body draft, side-by-side view.
   - **Approve dialog**: open, with a note typed.
   - **Prompt-injection warning**: ask “Tell me about ns-027”.
   - **Activity log** after approving one draft.
   - **Mobile**: the assistant panel full screen.
5. Save them as `docs/screenshots/NN-name.png` (for example `03-assistant.png`) and link them here.

Seed content is fictional and uses the reserved `.example` domain, so screenshots are safe to share.

## Limitations

- The demo agent is a keyword router: it understands a fixed set of request types, interprets only
  the latest message, and drafts only mechanical name replacements.
- The Claude provider has not been run against the live API in this repo's checks (that would cost
  money and need a key). Its replies aren't streamed.
- Search is case-insensitive substring matching: no stemming, ranking, or semantic search.
- Page bodies are shown as plain text; Markdown is not rendered.
- “Approve” updates the local SQLite store only; nothing is published anywhere.
- No authentication, roles, or multi-user editing; the reviewer is always “editor”.
- The activity log grows without limit and has no export.
- SQLite with one process is fine for local use; it isn't set up for concurrent production load.

## Future integrations

- **Real CMS adapters.** Implement `ContentRepository` for Contentstack, Contentful, or Sitecore
  using their delivery/management APIs. Approval would write back as a CMS *draft* through the
  management API, keeping the same compare-and-set check (CMS entry versions) and leaving publishing
  to the CMS's own workflow.
- **Semantic retrieval.** Add a local embedding model and vector store for “find pages about …”
  questions, exposed as another read-only tool.
- **Authentication and roles.** Editor vs reviewer roles, per-user activity attribution, and
  approval policies such as two-person review.
- **Scheduled audits.** Run the audit tools nightly and open drafts or notify editors.
- **Richer editing.** Rendered and sanitized Markdown preview, editing a draft before approving,
  and bulk approve with per-item confirmation.
- **Streaming assistant replies** and per-message cost reporting for the Claude provider.
- **Postgres** instead of SQLite for multi-user deployments.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Header says **Backend down**, or the UI shows “backend is unavailable (HTTP 500)” | Start the backend (see Quick start) and click the status indicator to recheck. |
| `node`, `npm`, or `uv` not found | Make sure they're on your `PATH` (for user-local installs, add `~/.local/bin`). |
| Demo counts differ from this README | Reset the data with `uv run python -m app.seed_db` and check `CMS_AUDIT_REFERENCE_DATE=2026-11-12`. |
| Assistant says a pending proposal already exists | Approve or reject the earlier draft first, or reset the data. |
| Port 3000 or 8000 in use | Stop the other process, or run on another port and update `BACKEND_URL` / `CMS_CORS_ORIGINS`. |
| Claude mode returns 503 | Read the message: usually a missing or invalid `ANTHROPIC_API_KEY`, a rate limit, or no network. The error is also in **Activity**. |

## Project docs

- [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md): goals, MVP scope, Definition of Done
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): original architecture plan
- [docs/BUILD_PROMPTS.md](docs/BUILD_PROMPTS.md): the phased build plan this repo followed
- [docs/seed-data.md](docs/seed-data.md): dataset and planted problems
- [docs/claude-provider.md](docs/claude-provider.md): optional Claude provider, billing, setup

## License

[MIT](LICENSE)
