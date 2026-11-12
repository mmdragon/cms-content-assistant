# Cursor / Claude Build Prompts — Project 1

## Phase 0 — inspect and plan

You are the senior engineer helping build this project. Read PROJECT_BRIEF.md and ARCHITECTURE.md.
First inspect the current workspace. Do not modify files yet.
Return:
1. proposed implementation plan in small milestones;
2. dependencies and why they are needed;
3. risks and security considerations;
4. exact commands to create the project;
5. questions only if genuinely blocking.
Keep the app local-first and free. Do not add paid services or require API keys.

## Phase 1 — scaffold

Implement the smallest working monorepo scaffold described in ARCHITECTURE.md.
Use Next.js/TypeScript for frontend and FastAPI/Pydantic for backend.
Add health endpoint, frontend health check, `.env.example`, `.gitignore`, and setup README.
Do not implement the AI agent yet. Run available checks and report exact results.

## Phase 2 — content repository

Implement SQLite models/repository, seed 30–50 fictional Northstar Living entries,
and endpoints to list, filter, search, and retrieve content.
Add tests. Include intentionally stale content, duplicate titles, missing metadata, and broken internal links.
Keep seed data fictional. Do not scrape copyrighted websites.

## Phase 3 — deterministic tools

Implement the allowlisted read tools and their typed schemas.
Add unit tests for each tool, invalid arguments, empty results, and error conditions.
Add proposal creation as pending-only. Do not apply edits from the agent.

## Phase 4 — user interface

Build a polished responsive content dashboard, content detail view, assistant panel,
proposal review with before/after diff, approve/reject controls, and activity log.
Use accessible controls, keyboard navigation, loading/empty/error states.
Do not overbuild visual effects.

## Phase 5 — mock agent

Implement a deterministic mock agent that routes a small set of supported natural-language intents
to the tools. Clearly label demo mode. Return evidence-backed findings, not fabricated claims.
Add a conversation UI and tests.

## Phase 6 — optional Claude integration

Before implementation, explain API billing and credential requirements.
Add a provider adapter so the mock mode remains available.
Keep credentials only on the backend in environment variables.
Use strict tool schemas, tool allowlists, timeouts, bounded iterations, and human approval.
Treat CMS content as untrusted input. Do not let page text change agent instructions.
Do not claim Claude subscription includes API usage.

## Phase 7 — finish

Review the project against the Definition of Done in PROJECT_BRIEF.md.
Run tests, lint, and type checks. Fix failures.
Update README with setup, demo prompts, architecture, limitations, and screenshots guidance.
Summarize files changed and commands actually run.
