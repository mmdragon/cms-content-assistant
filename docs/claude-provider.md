# Optional Claude provider

The app runs in **demo mode** by default: a deterministic, rule-based agent with no API key and
no cost. You can switch the assistant to **Claude** (via the Anthropic API) to handle free-form
questions. Everything else (tools, approval workflow, activity log) works the same either way.

## Billing and credentials: read this first

- **The Claude API is billed separately from a Claude.ai subscription.** A Claude Pro, Max, Team,
  or Enterprise plan does **not** include API usage. You need an Anthropic API account
  (console.anthropic.com) with a payment method or prepaid credits, and an API key from it.
- **You pay per token** (input and output) for every request. One assistant message can make
  several API requests because the model calls tools in a loop (capped at
  `CMS_CLAUDE_MAX_ITERATIONS`, default 8). Tool results such as page text count as input tokens.
- The default model is **Claude Opus 5.5** (`claude-opus-5-5`). At the time of writing its list price
  is $4 per million input tokens and $20 per million output tokens. Check the current price on
  Anthropic's pricing page before relying on it. Set `CMS_CLAUDE_MODEL` to use a different model;
  that changes the price.
- Rough sense of scale: a typical question here sends ~6-15K input tokens across the loop and gets
  ~1-2K output tokens back (the model's internal thinking is billed as output too), so roughly
  **$0.05-$0.10 per question** on Opus 5.5. This is an estimate,
  not a measurement; watch the usage page in the Anthropic Console, and set a spend limit there.
- **Server-side fallback** is on by default (`CMS_CLAUDE_FALLBACKS=true`): if Claude's safety
  classifiers decline a request, the API re-runs it on Anthropic's recommended fallback model in
  the same call, billed at that model's rates. Set it to `false` to turn this off.
- **Data**: with Claude enabled, the question, conversation history, and any page content the
  tools return are sent to Anthropic's API. The seed data is fictional, but keep this in mind if
  you load real content.

## Where the key lives

- The API key is read by the Anthropic SDK **in the backend process only**, from the
  `ANTHROPIC_API_KEY` environment variable (or a profile from `ant auth login`).
- It is not part of the app's settings, is never logged (the activity log redacts key-like values),
  and never reaches the browser: the frontend only talks to the backend through the `/api` proxy.
- Don't commit it. `.env` is git-ignored; `.env.example` has no key.

## Turning it on

1. Get an API key from the Anthropic Console and set a spend limit.
2. In the project's `.env` (the backend reads it when run from `backend/`), set:

   ```
   CMS_AGENT_PROVIDER=claude
   ```

   `.env` only supplies the app's `CMS_*` settings. The API key goes in the environment of the
   terminal that starts the backend (or use `ant auth login`):

   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

3. Restart the backend. The assistant panel's badge changes from **Demo mode** to **Claude**, and
   `/api/health` reports `"agent_provider": "claude"`.

To go back, set `CMS_AGENT_PROVIDER=mock` (or remove it) and restart.

| Setting | Default | Meaning |
|---|---|---|
| `CMS_AGENT_PROVIDER` | `mock` | `mock` (demo, free) or `claude` |
| `CMS_CLAUDE_MODEL` | `claude-opus-5-5` | Model id |
| `CMS_CLAUDE_EFFORT` | `medium` | `low` / `medium` / `high` / `xhigh` / `max`; higher means more thorough and more tokens |
| `CMS_CLAUDE_MAX_ITERATIONS` | `8` | Max model round-trips per message |
| `CMS_CLAUDE_MAX_TOKENS` | `16000` | Max output tokens per round-trip |
| `CMS_CLAUDE_TIMEOUT_SECONDS` | `60` | HTTP timeout per API request (SDK retries twice) |
| `CMS_CLAUDE_FALLBACKS` | `true` | Server-side refusal fallback |
| `CMS_AGENT_MAX_TOOL_CALLS` | `25` | Tool calls per message (shared with demo mode) |

## How the Claude provider stays safe

Implemented in `backend/app/agents/claude.py`:

- **Same tools, same guardrails.** The model calls the 7 allowlisted tools through the same
  registry as the demo agent: Pydantic argument validation (invalid arguments go back to the model
  as an error result), timeouts, output caps, per-message tool budget, and activity logging.
- **No write access.** The only tool with side effects is `create_edit_proposal`, which creates
  pending drafts and rejects evidence that isn't quoted from the page. Approval exists only as a
  human API endpoint.
- **Bounded loop.** At most `CMS_CLAUDE_MAX_ITERATIONS` round-trips and `CMS_AGENT_MAX_TOOL_CALLS`
  tool calls; `max_tokens`, `refusal`, and API errors all end the turn cleanly.
- **Untrusted content.** Tool results are wrapped in `<untrusted_tool_output>` tags, and the system
  prompt says page text is data, never instructions. The seed page `ns-027` contains a
  prompt-injection attempt for testing this.
- **Evidence you can check.** The findings and drafts shown under each answer come from tool
  output, not from the model's prose, so a claim the tools didn't support won't appear as evidence.
- **Clear failures.** Missing or invalid key, rate limits, network errors, and API errors return
  HTTP 503 with a plain-language message; the UI shows it with a retry button.

Tests (`backend/tests/test_claude_agent.py`) cover all of the above with a scripted fake client,
so the test suite never calls the API and never needs a key.

## Limitations

- Not exercised against the live API in this repo's automated checks (that would cost money and
  need a key). Try a few prompts by hand after enabling it.
- No streaming: the panel shows a "Checking the content…" indicator until the whole answer is ready.
- Only the text of earlier turns is sent as history; tool calls are re-run each turn as needed.
