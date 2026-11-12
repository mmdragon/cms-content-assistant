"""create_edit_proposal: the agent's only write-adjacent tool. It creates PENDING drafts only.

There is deliberately no tool to approve, apply, update, or delete anything.
"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.models.activity import Actor
from app.models.proposal import EditableField, ProposalStatus
from app.tools.base import Tool, ToolContext, ToolInput, ToolKind
from app.tools.content_tools import ContentId


class CreateEditProposalInput(ToolInput):
    content_id: ContentId
    field_name: EditableField
    proposed_value: Annotated[str, StringConstraints(min_length=1, max_length=20_000)]
    rationale: Annotated[str, StringConstraints(min_length=10, max_length=1000)] = Field(
        description="Why the change is needed, citing the finding."
    )
    evidence_excerpt: Annotated[str, StringConstraints(max_length=500)] = Field(
        default="",
        description="Exact text quoted from the current field value. Leave empty only when the "
        "field is currently empty.",
    )


class CreateEditProposalOutput(BaseModel):
    proposal_id: str
    content_id: str
    field_name: EditableField
    status: ProposalStatus
    created_at: datetime
    message: str


def create_edit_proposal(
    ctx: ToolContext, args: CreateEditProposalInput
) -> CreateEditProposalOutput:
    proposal = ctx.proposals.create(
        content_id=args.content_id,
        field_name=args.field_name,
        proposed_value=args.proposed_value,
        rationale=args.rationale,
        evidence_excerpt=args.evidence_excerpt,
        actor=Actor.ASSISTANT,
    )
    return CreateEditProposalOutput(
        proposal_id=proposal.id,
        content_id=proposal.content_id,
        field_name=proposal.field_name,
        status=proposal.status,
        created_at=proposal.created_at,
        message="Draft saved as pending. It will not be applied unless an editor approves it.",
    )


CREATE_EDIT_PROPOSAL = Tool(
    name="create_edit_proposal",
    description=(
        "Draft a change to one field (title, content, meta_title, meta_description) of one page. "
        "Creates a PENDING proposal only; a human must approve it before anything changes."
    ),
    kind=ToolKind.PROPOSE,
    input_model=CreateEditProposalInput,
    output_model=CreateEditProposalOutput,
    handler=create_edit_proposal,
)
