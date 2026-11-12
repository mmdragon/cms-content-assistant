"""Proposal lifecycle: create (pending only), approve (human only), reject (human only)."""

import uuid

from app.errors import ConflictError, InvalidInputError, NotFoundError
from app.models.activity import Actor, EventType
from app.models.proposal import MAX_PROPOSED_LENGTH, EditableField, Proposal, ProposalStatus
from app.repositories.base import ContentRepository
from app.repositories.proposals import ApplyOutcome, SQLiteProposalRepository
from app.services.audit import AuditService, Clock, utc_now
from app.tools.findings import normalize_ws

EMPTY_FIELD_EVIDENCE = "(field is empty)"


def _strip_ellipses(text: str) -> str:
    return text.strip().strip("…").strip().removesuffix("...").removeprefix("...").strip()


class ProposalService:
    def __init__(
        self,
        content_repo: ContentRepository,
        proposal_repo: SQLiteProposalRepository,
        audit: AuditService,
        clock: Clock = utc_now,
    ) -> None:
        self._content = content_repo
        self._proposals = proposal_repo
        self._audit = audit
        self._clock = clock

    # ---- create (agent-callable via the create_edit_proposal tool) --------

    def create(
        self,
        *,
        content_id: str,
        field_name: EditableField,
        proposed_value: str,
        rationale: str,
        evidence_excerpt: str,
        actor: Actor,
    ) -> Proposal:
        entry = self._content.get_content(content_id)
        if entry is None:
            raise NotFoundError(f"Unable to verify: no content with id '{content_id}'.")

        original: str | None = getattr(entry, field_name.value)
        proposed = proposed_value.strip()
        if not proposed:
            raise InvalidInputError("proposed_value must not be empty.")
        limit = MAX_PROPOSED_LENGTH[field_name]
        if len(proposed) > limit:
            raise InvalidInputError(f"proposed_value exceeds {limit} characters for {field_name}.")
        if original is not None and proposed == original.strip():
            raise InvalidInputError("proposed_value is identical to the current value.")

        evidence = self._verify_evidence(original, evidence_excerpt, field_name)

        existing = self._proposals.find_pending(content_id, field_name)
        if existing is not None:
            raise ConflictError(
                f"A pending proposal ({existing.id}) already exists for {content_id}.{field_name}. "
                "Approve or reject it first."
            )

        proposal = Proposal(
            id=f"prop-{uuid.uuid4().hex[:12]}",
            content_id=content_id,
            field_name=field_name,
            original_value=original,
            proposed_value=proposed,
            rationale=rationale.strip(),
            evidence_excerpt=evidence,
            status=ProposalStatus.PENDING,
            created_at=self._clock(),
        )
        self._proposals.add(proposal)
        self._audit.record(
            EventType.PROPOSAL_CREATED,
            actor=actor,
            status="pending",
            details={
                "proposal_id": proposal.id,
                "content_id": content_id,
                "field_name": field_name.value,
                "rationale": proposal.rationale,
            },
        )
        return proposal

    @staticmethod
    def _verify_evidence(original: str | None, excerpt: str, field_name: EditableField) -> str:
        """Evidence must be quoted from the current value, so findings can't be fabricated."""
        if not (original or "").strip():
            return EMPTY_FIELD_EVIDENCE
        needle = normalize_ws(_strip_ellipses(excerpt))
        if not needle:
            raise InvalidInputError(
                f"evidence_excerpt is required: quote the text in {field_name} being changed."
            )
        if needle.casefold() not in normalize_ws(original or "").casefold():
            raise InvalidInputError(
                f"evidence_excerpt was not found in the current {field_name}. "
                "Unable to verify; quote the page text exactly."
            )
        return needle

    # ---- review (human-only, via API) --------------------------------------

    def get(self, proposal_id: str) -> Proposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise NotFoundError(f"Proposal '{proposal_id}' not found")
        return proposal

    def approve(self, proposal_id: str, *, note: str | None = None) -> Proposal:
        outcome = self._proposals.approve_and_apply(proposal_id, self._clock(), note)
        return self._finish_review(proposal_id, outcome, EventType.PROPOSAL_APPROVED, note)

    def reject(self, proposal_id: str, *, note: str | None = None) -> Proposal:
        outcome = self._proposals.reject(proposal_id, self._clock(), note)
        return self._finish_review(proposal_id, outcome, EventType.PROPOSAL_REJECTED, note)

    def _finish_review(
        self, proposal_id: str, outcome: ApplyOutcome, event: EventType, note: str | None
    ) -> Proposal:
        details = {"proposal_id": proposal_id, "outcome": outcome.value, "note": note}
        if outcome is ApplyOutcome.NOT_FOUND:
            raise NotFoundError(f"Proposal '{proposal_id}' not found")

        proposal = self.get(proposal_id)
        details |= {"content_id": proposal.content_id, "field_name": proposal.field_name.value}
        if outcome is ApplyOutcome.APPLIED:
            self._audit.record(event, actor=Actor.EDITOR, status="ok", details=details)
            return proposal

        self._audit.record(event, actor=Actor.EDITOR, status="conflict", details=details)
        if outcome is ApplyOutcome.NOT_PENDING:
            raise ConflictError(f"Proposal '{proposal_id}' is already {proposal.status.value}.")
        raise ConflictError(
            f"The page's {proposal.field_name} changed after this proposal was drafted, so it "
            "was not applied. Reject it and draft a new proposal."
        )
