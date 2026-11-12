"""Deterministic, rule-based agent for demo mode. No model and no API key.

It routes a small set of supported requests to allowlisted tools and builds its answer only
from tool output, so every finding cites a page id and an excerpt that exists in the data.
Page text is never interpreted as instructions: it is only searched and quoted.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.agents.base import (
    AgentResponse,
    ChatRequest,
    ProposalRef,
    ToolBudgetExceeded,
    ToolRunner,
)
from app.models.proposal import EditableField
from app.tools.base import ToolStatus
from app.tools.findings import Finding, find_excerpt

MAX_PROPOSALS_PER_TURN = 10
DEFAULT_STALE_DAYS = 540
PROPOSAL_FIELDS = (
    EditableField.TITLE,
    EditableField.META_TITLE,
    EditableField.META_DESCRIPTION,
    EditableField.CONTENT,
)


@dataclass(frozen=True)
class TermRule:
    key: str
    term: str
    replacement: str
    reason: str
    triggers: tuple[re.Pattern[str], ...]


TERM_RULES: tuple[TermRule, ...] = (
    TermRule(
        key="discontinued_plan",
        term="Northstar Classic",
        replacement="Northstar Care",
        reason="The Northstar Classic plan was discontinued and replaced by Northstar Care.",
        triggers=(re.compile(r"\bnorthstar classic\b"), re.compile(r"\bclassic\b")),
    ),
    TermRule(
        key="old_brand",
        term="Northstar Homes",
        replacement="Northstar Living",
        reason="The company rebranded from Northstar Homes to Northstar Living.",
        triggers=(
            re.compile(r"\bnorthstar homes\b"),
            re.compile(r"\b(old|former|previous) (brand|company|business) name\b"),
            re.compile(r"\brebrand"),
        ),
    ),
)

_RE = {
    "page_id": re.compile(r"\bns-\d{3}\b"),
    "metadata": re.compile(
        r"\bmeta\b|\bmetadata\b|\bseo\b|\bmeta[- ]?(titles?|descriptions?)\b|\btitle tags?\b"
        r"|\bcanonical\b|\bdescriptions?\b"
    ),
    "stale": re.compile(
        r"\b(outdated|stale|out[- ]of[- ]date|old (pages|content|posts)|freshness|last updated"
        r"|(not|n'?t) (been )?updated)\b"
    ),
    "duplicates": re.compile(r"\bduplicat\w*|\b(same|identical) titles?\b|\bdupes?\b"),
    "links": re.compile(r"\blinks?\b|\b404s?\b"),
    "audit": re.compile(
        r"\baudit\b|\boverview\b|\bhealth ?check\b|\ball (the )?(issues|problems)\b"
        r"|\bwhat'?s wrong\b|\bfull report\b"
    ),
    "help": re.compile(r"\bhelp\b|\bwhat can you do\b|\bhow do i use\b"),
    "propose": re.compile(
        r"\b(suggest|propos|draft|rewrit|rewor|replac|fix|correct|edit)\w*"
        r"|\bupdated? (the )?wording\b|\bnew wording\b"
    ),
    "write_verb": re.compile(r"\b(approv|apply|applie|publish|delet|remov|deploy|push live)\w*"),
    "negation": re.compile(r"\b(don'?t|do not|does not|not|never|without|no|nor|avoid)\b"),
    "quoted": re.compile(r"[\"“”]([^\"“”]{2,80})[\"“”]"),
    "mention": re.compile(
        r"\b(?:mention|mentions|mentioning|contain|contains|containing|reference|references"
        r"|referencing|search for|search)\s+(?:the\s+)?(?:phrase\s+|word\s+|term\s+)?"
        r"([a-z0-9][\w'\- ]{1,60}?)\s*(?:[?.!,]|$)"
    ),
    "duration": re.compile(r"\b(\d{1,4}|a|an|one|two|three|six)\s*(day|week|month|year)s?\b"),
}

_NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "six": 6}
_UNIT_DAYS = {"day": 1, "week": 7, "year": 365}

_INJECTION = re.compile(
    r"ignore (all )?(previous|prior|above) instructions"
    r"|\b(system|developer) (notice|prompt|message)\b"
    r"|\bto ai assistants?\b|\bapprove (every|all) (pending )?proposals?\b",
    re.I,
)

HELP_TEXT = (
    "I'm the demo assistant. I'm rule-based (no AI model), so I understand a fixed set of "
    "requests. Try:\n"
    "• “Find pages that still mention the discontinued Northstar Classic plan. Suggest updated "
    "wording.”\n"
    "• “Which pages still use the old brand name Northstar Homes?”\n"
    "• “Which pages have missing or overly long metadata?”\n"
    "• “List pages not updated in the last 18 months.”\n"
    "• “Are there duplicate titles?”\n"
    "• “Check for broken internal links.”\n"
    "• “Tell me about ns-008.”\n"
    "• “Run a full audit.”\n"
    '• Search for a phrase in quotes, e.g. “Which pages mention "splash pad"?”'
)

WRITE_REFUSAL = (
    "I can't approve, apply, publish, or delete anything. I can only draft proposals; an editor "
    "approves or rejects each one on the Proposals screen."
)


@dataclass
class Plan:
    page_ids: list[str] = field(default_factory=list)
    term_rules: list[TermRule] = field(default_factory=list)
    search_phrase: str | None = None
    stale_days: int | None = None
    metadata: bool = False
    duplicates: bool = False
    links: bool = False
    wants_proposals: bool = False
    write_request: bool = False

    @property
    def intents(self) -> list[str]:
        out = [f"page:{p}" for p in self.page_ids]
        out += [f"term:{r.key}" for r in self.term_rules]
        if self.search_phrase:
            out.append("search")
        if self.stale_days is not None:
            out.append("stale")
        if self.metadata:
            out.append("metadata")
        if self.duplicates:
            out.append("duplicates")
        if self.links:
            out.append("links")
        return out


def _parse_days(text: str) -> int:
    match = _RE["duration"].search(text)
    if not match:
        return DEFAULT_STALE_DAYS
    raw, unit = match.group(1), match.group(2)
    count = _NUMBER_WORDS.get(raw) or int(raw)
    days = round(count * 365 / 12) if unit == "month" else count * _UNIT_DAYS[unit]
    return max(30, min(3650, days))


def _has_unnegated_write(text: str) -> bool:
    for m in _RE["write_verb"].finditer(text):
        prefix = text[max(0, m.start() - 30) : m.start()]
        if not _RE["negation"].search(prefix):
            return True
    return False


def parse(message: str) -> Plan:
    text = " ".join(message.lower().split())
    plan = Plan()
    plan.page_ids = list(dict.fromkeys(_RE["page_id"].findall(text)))[:3]
    plan.term_rules = [r for r in TERM_RULES if any(t.search(text) for t in r.triggers)]

    quoted = _RE["quoted"].search(message)
    if quoted:
        phrase = quoted.group(1).strip()
        if not any(phrase.lower() == r.term.lower() for r in plan.term_rules):
            plan.search_phrase = phrase
    elif not plan.term_rules and not plan.page_ids:
        mention = _RE["mention"].search(text)
        if mention and not _RE["links"].search(mention.group(1)):
            plan.search_phrase = mention.group(1).strip()

    audit = bool(_RE["audit"].search(text))
    if audit or _RE["stale"].search(text):
        plan.stale_days = _parse_days(text)
    plan.metadata = audit or bool(_RE["metadata"].search(text))
    plan.duplicates = audit or bool(_RE["duplicates"].search(text))
    plan.links = audit or bool(_RE["links"].search(text))
    plan.wants_proposals = bool(_RE["propose"].search(text))
    plan.write_request = _has_unnegated_write(text)
    return plan


def _plural(n: int, word: str, plural: str | None = None) -> str:
    return f"{n} {word if n == 1 else (plural or word + 's')}"


def _verb(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


class _Turn:
    """Accumulates one response."""

    def __init__(self, tools: ToolRunner) -> None:
        self.tools = tools
        self.paragraphs: list[str] = []
        self.findings: list[Finding] = []
        self.proposals: list[ProposalRef] = []
        self.notes: list[str] = []
        self._warned_ids: set[str] = set()

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)

    def screen_untrusted(self, content_id: str, text: str | None) -> None:
        """Flag page text that tries to instruct the assistant. It is never acted on."""
        if text and _INJECTION.search(text) and content_id not in self._warned_ids:
            self._warned_ids.add(content_id)
            self.note(
                f"{content_id} contains text addressed to AI assistants (it asks them to ignore "
                "their instructions). I treated it as page content and did not act on it. "
                "Consider removing it."
            )

    def add_findings(self, raw: list[dict[str, Any]]) -> list[Finding]:
        items = [Finding.model_validate(f) for f in raw]
        for f in items:
            self.screen_untrusted(f.content_id, f.excerpt)
        self.findings.extend(items)
        return items

    def tool_failed(self, what: str, error: str | None) -> None:
        self.paragraphs.append(
            f"I couldn't {what}: {error or 'the tool failed'}. Unable to verify."
        )


class MockAgent:
    name = "mock"
    demo_mode = True

    def respond(self, request: ChatRequest, tools: ToolRunner) -> AgentResponse:
        plan = parse(request.latest)
        turn = _Turn(tools)

        try:
            for content_id in plan.page_ids:
                self._page(turn, content_id)
            for rule in plan.term_rules:
                self._term(turn, rule, propose=plan.wants_proposals)
            if plan.search_phrase:
                self._search(turn, plan.search_phrase)
            if plan.stale_days is not None:
                self._stale(turn, plan.stale_days, plan.wants_proposals)
            if plan.metadata:
                self._metadata(turn, plan.wants_proposals)
            if plan.duplicates:
                self._duplicates(turn)
            if plan.links:
                self._links(turn)
        except ToolBudgetExceeded as exc:
            turn.note(f"I stopped early because the {exc}. Ask a narrower question to see more.")

        if plan.write_request and plan.intents:
            turn.note(WRITE_REFUSAL)

        if not plan.intents:
            message = HELP_TEXT if not plan.write_request else WRITE_REFUSAL + "\n\n" + HELP_TEXT
        else:
            parts = list(turn.paragraphs)
            if turn.proposals:
                parts.append(
                    f"Nothing has been changed. The {_plural(len(turn.proposals), 'draft')} "
                    "above are pending until you approve them on the Proposals screen."
                )
            message = "\n\n".join(parts)

        return AgentResponse(
            provider=self.name,
            demo_mode=self.demo_mode,
            intents=plan.intents or ["help"],
            message=message,
            findings=turn.findings,
            proposals=turn.proposals,
            tool_calls=tools.calls,
            notes=turn.notes,
        )

    # ---- handlers ----------------------------------------------------------

    def _term(self, turn: _Turn, rule: TermRule, *, propose: bool) -> None:
        search = turn.tools.run("search_content", {"query": rule.term, "limit": 50})
        if not search.ok or search.output is None:
            turn.tool_failed(f"search for “{rule.term}”", search.error)
            return
        matches = search.output["matches"]
        if not matches:
            turn.paragraphs.append(f"No pages mention “{rule.term}”.")
            return

        places = 0
        drafted_before = len(turn.proposals)
        for match in matches:
            doc_result = turn.tools.run("get_content_by_id", {"content_id": match["content_id"]})
            if not doc_result.ok or doc_result.output is None:
                turn.note(f"Couldn't load {match['content_id']}; unable to verify its text.")
                continue
            doc = doc_result.output
            turn.screen_untrusted(doc["content_id"], doc["content"])
            for fld in PROPOSAL_FIELDS:
                value: str = doc.get(fld.value) or ""
                excerpt = find_excerpt(value, rule.term)
                if excerpt is None:
                    continue
                places += 1
                turn.findings.append(
                    Finding(
                        content_id=doc["content_id"],
                        title=doc["title"],
                        issue=rule.key,
                        field=fld.value,
                        excerpt=excerpt,
                        reason=f"Mentions “{rule.term}”. {rule.reason}",
                        recommendation=f"Replace “{rule.term}” with “{rule.replacement}” and "
                        "check that the surrounding details are still accurate.",
                        severity="high",
                    )
                )
                if propose:
                    if fld is EditableField.CONTENT and doc["content_truncated"]:
                        turn.note(f"{doc['content_id']} is too long to rewrite safely; skipped.")
                        continue
                    self._propose_replacement(turn, rule, doc, fld, value, excerpt)
            slug_term = rule.term.lower().replace(" ", "-")
            if slug_term in doc["slug"]:
                turn.note(
                    f"The URL /{doc['slug']} ({doc['content_id']}) also contains the old name. "
                    "Slugs can't be changed through proposals because that would break links; "
                    "set up a redirect if you rename it."
                )

        pages = len({f.content_id for f in turn.findings if f.issue == rule.key})
        text = (
            f"{_plural(pages, 'page')} {_verb(pages, 'mentions', 'mention')} “{rule.term}” "
            f"({_plural(places, 'place')} in total). {rule.reason} "
            "Each place is listed with the exact excerpt."
        )
        drafted = len(turn.proposals) - drafted_before
        if propose:
            text += (
                f" I drafted {_plural(drafted, 'proposal')} replacing it with "
                f"“{rule.replacement}”. "
                "I only swapped the name; other details in those sentences (like coverage terms) "
                "were not changed, so please check them before approving."
            )
        else:
            text += " Ask me to suggest updated wording and I'll draft proposals for you to review."
        turn.paragraphs.append(text)

    def _propose_replacement(
        self,
        turn: _Turn,
        rule: TermRule,
        doc: dict[str, Any],
        fld: EditableField,
        value: str,
        excerpt: str,
    ) -> None:
        if len(turn.proposals) >= MAX_PROPOSALS_PER_TURN:
            turn.note(
                f"I drafted the maximum of {MAX_PROPOSALS_PER_TURN} proposals for one request. "
                "Review those, then ask again for the rest."
            )
            return
        proposed = re.sub(re.escape(rule.term), rule.replacement, value, flags=re.I)
        result = turn.tools.run(
            "create_edit_proposal",
            {
                "content_id": doc["content_id"],
                "field_name": fld.value,
                "proposed_value": proposed,
                "rationale": f"{rule.reason} Replaced “{rule.term}” with “{rule.replacement}”. "
                "Nothing else in the text was changed; verify any details such as coverage terms.",
                "evidence_excerpt": excerpt,
            },
        )
        if result.ok and result.output is not None:
            turn.proposals.append(
                ProposalRef(
                    proposal_id=result.output["proposal_id"],
                    content_id=doc["content_id"],
                    title=doc["title"],
                    field_name=fld,
                )
            )
        elif result.status is ToolStatus.CONFLICT:
            turn.note(
                f"{doc['content_id']} {fld.value}: a pending proposal already exists, so I didn't "
                "draft another."
            )
        else:
            turn.note(
                f"Couldn't draft a proposal for {doc['content_id']} {fld.value}: {result.error}"
            )

    def _search(self, turn: _Turn, phrase: str) -> None:
        result = turn.tools.run("search_content", {"query": phrase[:200], "limit": 25})
        if not result.ok or result.output is None:
            turn.tool_failed(f"search for “{phrase}”", result.error)
            return
        out = result.output
        for m in out["matches"]:
            turn.screen_untrusted(m["content_id"], m["excerpt"])
            turn.findings.append(
                Finding(
                    content_id=m["content_id"],
                    title=m["title"],
                    issue="mentions_phrase",
                    field=m["matched_fields"][0] if m["matched_fields"] else "content",
                    excerpt=m["excerpt"],
                    reason=f"Mentions “{phrase}” (in {', '.join(m['matched_fields'])}).",
                    recommendation="Review whether this mention is still accurate.",
                    severity="low",
                )
            )
        total = out["total_found"]
        if total == 0:
            turn.paragraphs.append(f"No pages mention “{phrase}”.")
        else:
            shown = len(out["matches"])
            more = f" Showing the first {shown}." if out["truncated"] else ""
            verb = _verb(total, "mentions", "mention")
            turn.paragraphs.append(f"{_plural(total, 'page')} {verb} “{phrase}”.{more}")

    def _stale(self, turn: _Turn, days: int, propose: bool) -> None:
        result = turn.tools.run("find_outdated_content", {"days_old": days, "limit": 50})
        if not result.ok or result.output is None:
            turn.tool_failed("check for outdated pages", result.error)
            return
        out = result.output
        turn.add_findings(out["findings"])
        if out["total_found"] == 0:
            turn.paragraphs.append(
                f"Every page has been updated within the last {days} days (as of {out['as_of']})."
            )
        else:
            turn.paragraphs.append(
                f"{_plural(out['total_found'], 'page')} "
                f"{_verb(out['total_found'], 'hasn’t', 'haven’t')} been updated in "
                f"{days} days or more "
                f"(before {out['cutoff']}, as of {out['as_of']}), listed oldest first."
            )
        if propose:
            turn.note(
                "I don't draft edits for outdated pages: bringing them up to date needs facts I "
                "can't verify. Review each one and update or archive it."
            )

    def _metadata(self, turn: _Turn, propose: bool) -> None:
        result = turn.tools.run("check_metadata", {"limit": 100})
        if not result.ok or result.output is None:
            turn.tool_failed("check metadata", result.error)
            return
        out = result.output
        turn.add_findings(out["findings"])
        labels = {
            "missing_meta_description": ("missing meta description", "missing meta descriptions"),
            "meta_description_too_long": (
                "meta description over 160 characters",
                "meta descriptions over 160 characters",
            ),
            "missing_meta_title": ("missing meta title", "missing meta titles"),
            "meta_title_too_long": (
                "meta title over 60 characters",
                "meta titles over 60 characters",
            ),
            "missing_canonical_url": ("missing canonical URL", "missing canonical URLs"),
            "canonical_url_mismatch": ("mismatched canonical URL", "mismatched canonical URLs"),
        }
        parts = [
            f"{n} {labels[k][0] if n == 1 else labels[k][1]}" if k in labels else f"{n} × {k}"
            for k, n in out["counts"].items()
        ]
        if not parts:
            turn.paragraphs.append("No metadata problems found.")
        else:
            turn.paragraphs.append(
                f"I found {_plural(out['total_found'], 'metadata issue')}: {', '.join(parts)}."
            )
        if propose and parts:
            turn.note(
                "In demo mode I don't write new meta titles or descriptions, because that means "
                "inventing copy. Each finding shows exactly what to fix."
            )

    def _duplicates(self, turn: _Turn) -> None:
        result = turn.tools.run("find_duplicate_titles", {})
        if not result.ok or result.output is None:
            turn.tool_failed("check for duplicate titles", result.error)
            return
        out = result.output
        turn.add_findings(out["findings"])
        groups = out["groups"]
        if not groups:
            turn.paragraphs.append("No two pages share a title.")
        else:
            listed = "; ".join(f"“{g['title']}” ({', '.join(g['content_ids'])})" for g in groups)
            turn.paragraphs.append(
                f"{_plural(len(groups), 'title is', 'titles are')} used by more than one page: "
                f"{listed}."
            )

    def _links(self, turn: _Turn) -> None:
        result = turn.tools.run("check_internal_links", {"limit": 100})
        if not result.ok or result.output is None:
            turn.tool_failed("check internal links", result.error)
            return
        out = result.output
        turn.add_findings(out["findings"])
        if out["total_found"] == 0:
            turn.paragraphs.append(
                f"All {out['links_checked']} internal links across {out['pages_checked']} pages "
                "point to published pages."
            )
        else:
            turn.paragraphs.append(
                f"I checked {out['links_checked']} internal links across {out['pages_checked']} "
                f"pages and found {_plural(out['total_found'], 'problem')}."
            )

    def _page(self, turn: _Turn, content_id: str) -> None:
        result = turn.tools.run("get_content_by_id", {"content_id": content_id})
        if result.status is ToolStatus.NOT_FOUND:
            turn.paragraphs.append(
                f"I couldn't find a page with id {content_id}. Unable to verify."
            )
            return
        if not result.ok or result.output is None:
            turn.tool_failed(f"load {content_id}", result.error)
            return
        doc = result.output
        turn.screen_untrusted(content_id, doc["content"])
        if content_id in turn._warned_ids:
            match = _INJECTION.search(doc["content"])
            excerpt = find_excerpt(doc["content"], match.group(0)) if match else None
            turn.findings.append(
                Finding(
                    content_id=content_id,
                    title=doc["title"],
                    issue="embedded_instructions",
                    field="content",
                    excerpt=excerpt or "",
                    reason="The page contains text addressed to AI assistants, which may be a "
                    "prompt-injection attempt.",
                    recommendation="Remove the embedded instruction text from the page.",
                    severity="high",
                )
            )

        page_findings: list[dict[str, Any]] = []
        for name, args in (
            ("check_metadata", {"limit": 100}),
            ("check_internal_links", {"content_id": content_id}),
            ("find_outdated_content", {"days_old": DEFAULT_STALE_DAYS, "limit": 50}),
        ):
            res = turn.tools.run(name, args)
            if res.ok and res.output is not None:
                page_findings += [
                    f for f in res.output["findings"] if f["content_id"] == content_id
                ]
            else:
                turn.note(f"Couldn't run {name} for {content_id}: {res.error}")
        turn.add_findings(page_findings)

        summary = (
            f"{doc['title']} ({content_id}) is a {doc['status']} {doc['category']} page at "
            f"/{doc['slug']}, last updated {doc['updated_at'][:10]}."
        )
        issues = len(page_findings) + (1 if content_id in turn._warned_ids else 0)
        summary += (
            f" I found {_plural(issues, 'issue')} on it." if issues else " I found no issues on it."
        )
        turn.paragraphs.append(summary)
