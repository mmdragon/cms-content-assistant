# Architecture — CMS Assistant

## High-level flow

Browser (Next.js) → FastAPI REST API → Agent service → allowlisted tools → content repository (SQLite).
The agent service may use a mock provider initially and a Claude-backed provider later.
The frontend never receives model API secrets.

## Suggested repository structure

cms-content-assistant/
  frontend/
    app/
    components/
    lib/
    types/
  backend/
    app/
      main.py
      api/
      agents/
      tools/
      services/
      repositories/
      models/
      schemas/
    tests/
    seed/
  docs/
  .env.example
  .gitignore
  README.md

## Backend boundaries

- API routes: request/response handling only.
- Agent service: manages agent loop and tool selection.
- Tool functions: narrow, typed operations with validated input/output.
- Repository: all SQLite access.
- Provider adapter: mock provider now; optional Claude provider later.
- Audit service: records tool executions and approvals.

## Suggested API endpoints

GET /api/health
GET /api/content
GET /api/content/{content_id}
POST /api/assistant/chat
GET /api/proposals
GET /api/proposals/{proposal_id}
POST /api/proposals/{proposal_id}/approve
POST /api/proposals/{proposal_id}/reject
GET /api/activity

## Data entities

ContentEntry:
id, title, slug, content, category, status, created_at, updated_at,
meta_title, meta_description, canonical_url, tags_json.

Proposal:
id, content_id, field_name, original_value, proposed_value, rationale,
evidence_excerpt, status (pending/approved/rejected), created_at, reviewed_at.

ActivityEvent:
id, event_type, actor, tool_name, details_json, status, created_at.

## Agent tools

- search_content(query, category?, status?)
- get_content_by_id(content_id)
- find_outdated_content(days_old)
- find_duplicate_titles()
- audit_metadata()
- check_internal_links()
- create_edit_proposal(content_id, field_name, proposed_value, rationale, evidence_excerpt)

Important: create_edit_proposal creates a pending proposal only. A separate API approval action applies it.
The agent must not have a direct unrestricted database-write tool.

## Future CMS adapter

Define a ContentRepository interface. Implement SQLiteContentRepository first.
A future Contentstack/Contentful/Sitecore adapter can implement the same interface.
Do not make the MVP depend on a vendor account or vendor SDK.
