# CMS Content Assistant

A local-first, portfolio-quality web app that helps a content editor search a simulated headless CMS,
find stale or problematic pages, and review AI-proposed edits. **The assistant never changes content
without explicit human approval.**

> Status: **Phase 1 — scaffold.** Health check only. Content, tools, UI, and the mock agent arrive in
> later phases (see [docs/BUILD_PROMPTS.md](docs/BUILD_PROMPTS.md)).

## Architecture

```
Browser ──► Next.js (frontend, :3000) ──/api/* proxy──► FastAPI (backend, :8000) ──► agent ──► allowlisted tools ──► SQLite
```

- The browser only talks to the Next.js server. `/api/*` is rewritten to the backend
  (`frontend/next.config.ts`), so the backend URL and any future model keys stay server-side.
- Backend layout follows [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): `api/` (routes only),
  `agents/`, `tools/`, `services/`, `repositories/`, `models/`, `schemas/`.

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
| `BACKEND_URL` | frontend (`frontend/.env.local`) | `http://127.0.0.1:8000` | Proxy target for `/api/*` |

## API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness + app version, environment, agent provider |

## Limitations (current phase)

- No content, search, tools, agent, or proposals yet.
- No authentication (out of scope for the MVP; the backend binds to `127.0.0.1` only).
