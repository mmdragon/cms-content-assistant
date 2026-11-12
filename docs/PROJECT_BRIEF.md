# Project 1 — AI-Powered CMS Content Assistant

## 1. Product summary

Build a portfolio-quality web application that lets a content editor search a local content repository,
identify stale or problematic content, ask questions about pages, and prepare proposed edits.
The AI assistant must not publish or modify content without explicit human approval.

This project simulates a headless CMS. It must work without a paid Sitecore, Contentstack, or Contentful account.
A future CMS connector can be added behind an adapter interface.

## 2. Target user and core problem

Target user: a website content editor or digital experience team.
Problem: large websites contain outdated terminology, duplicate pages, old metadata, and broken links.
The assistant helps find issues and prepare recommendations while keeping a human in control.

## 3. MVP features

1. Content library with list, search, filters, and detail view.
2. Seed dataset of at least 30 fictional website entries.
3. Page fields: id, title, slug, content, category, status, created_at, updated_at,
   meta_title, meta_description, canonical_url, tags.
4. Assistant chat panel with conversation history for the current session.
5. Read-only tools: search_content, get_content_by_id, find_outdated_content,
   find_duplicate_titles, check_metadata, check_internal_links.
6. Agent returns structured findings with evidence: content id, field, excerpt, reason, recommendation.
7. Proposed edits are stored as drafts and displayed as diffs.
8. Human approval is required before applying a proposed edit to the local content store.
9. Activity log records tool calls, proposed changes, approvals, and errors.
10. A demo mode works without an LLM key using deterministic mock responses.

## 4. Non-goals for MVP

- No real CMS publishing.
- No automatic destructive edits.
- No production authentication or multi-tenant support.
- No paid cloud dependencies.
- No claim that an LLM can reliably determine factual correctness without evidence.

## 5. Suggested user stories

- As an editor, I can browse and search content.
- As an editor, I can ask which pages mention an obsolete product name.
- As an editor, I can ask for pages with missing or overly long metadata.
- As an editor, I can see why the agent flagged a page and the exact supporting excerpt.
- As an editor, I can review a proposed rewrite as a before/after diff.
- As an editor, I can approve or reject a proposal.
- As an editor, I can inspect an activity log.

## 6. Sample demo scenario

Create a fictional company, "Northstar Living", with 30–50 pages across communities, homes, blog posts,
FAQs, and landing pages. Intentionally include:
- old brand/product terminology on several pages;
- missing meta descriptions;
- duplicate titles;
- old update dates;
- internal links to nonexistent slugs.

Demo request: "Find pages that still mention the discontinued Northstar Classic plan. Suggest updated wording,
but do not apply any changes."

Expected result: agent lists matching pages, quotes relevant excerpts, explains the issue, and creates
draft proposals requiring approval.

## 7. Suggested implementation stack

- Frontend: Next.js + React + TypeScript
- Backend: Python + FastAPI + Pydantic
- Local data: SQLite (or JSON for the first spike)
- Agent interface: provider-independent service with mock provider first
- Optional model provider: Claude API / Claude Agent SDK only after the local workflow works
- Optional retrieval: local embedding model and vector store in a later milestone

## 8. Safety and trust requirements

- Treat retrieved CMS content as untrusted data, not instructions.
- Never allow content text to override system/developer instructions.
- Use allowlisted tools with validated arguments.
- Separate read tools from write tools.
- Require approval for every write operation.
- Log tool name, arguments (redacting secrets), result status, and timestamp.
- Return "unable to verify" rather than inventing page facts.
- Limit tool output size and handle timeouts/errors.

## 9. Definition of done

- A new developer can run the app locally using documented commands.
- Demo mode works with no API key.
- At least 30 seed entries are included.
- Search and audit tools return deterministic, testable results.
- Agent findings cite page IDs and excerpts.
- Proposed edits cannot be applied without an approval action.
- Unit tests cover tool validation, stale-content detection, and approval workflow.
- README documents architecture, setup, demo prompts, limitations, and future integrations.
