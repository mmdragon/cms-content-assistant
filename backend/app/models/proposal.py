"""Edit proposals: drafts created by the assistant that only a human can apply."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EditableField(StrEnum):
    """The only content fields a proposal may change. Anything else is rejected."""

    TITLE = "title"
    CONTENT = "content"
    META_TITLE = "meta_title"
    META_DESCRIPTION = "meta_description"


# Upper bounds on proposed values, per field.
MAX_PROPOSED_LENGTH: dict[EditableField, int] = {
    EditableField.TITLE: 200,
    EditableField.CONTENT: 20_000,
    EditableField.META_TITLE: 120,
    EditableField.META_DESCRIPTION: 320,
}


class Proposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    content_id: str
    field_name: EditableField
    original_value: str | None
    proposed_value: str
    rationale: str
    evidence_excerpt: str
    status: ProposalStatus
    created_at: datetime
    reviewed_at: datetime | None = None
    review_note: str | None = None
