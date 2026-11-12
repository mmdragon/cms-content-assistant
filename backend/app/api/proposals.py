"""Human review of proposals. Approval is the only path that changes content."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import AppContainer
from app.models.content import CONTENT_ID_PATTERN
from app.models.proposal import Proposal, ProposalStatus

router = APIRouter(prefix="/proposals", tags=["proposals"])

PROPOSAL_ID_PATTERN = r"^prop-[a-f0-9]{12}$"
ProposalId = Annotated[str, Path(pattern=PROPOSAL_ID_PATTERN)]


class ProposalListResponse(BaseModel):
    items: list[Proposal]
    total: int
    limit: int
    offset: int


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=500)


@router.get("", response_model=ProposalListResponse)
def list_proposals(
    container: AppContainer,
    status: ProposalStatus | None = None,
    content_id: Annotated[str | None, Query(pattern=CONTENT_ID_PATTERN)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ProposalListResponse:
    items, total = container.proposal_repo.list(
        status=status, content_id=content_id, limit=limit, offset=offset
    )
    return ProposalListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{proposal_id}", response_model=Proposal)
def get_proposal(container: AppContainer, proposal_id: ProposalId) -> Proposal:
    return container.proposals.get(proposal_id)


@router.post("/{proposal_id}/approve", response_model=Proposal)
def approve_proposal(
    container: AppContainer,
    proposal_id: ProposalId,
    review: Annotated[ReviewRequest | None, Body()] = None,
) -> Proposal:
    return container.proposals.approve(proposal_id, note=review.note if review else None)


@router.post("/{proposal_id}/reject", response_model=Proposal)
def reject_proposal(
    container: AppContainer,
    proposal_id: ProposalId,
    review: Annotated[ReviewRequest | None, Body()] = None,
) -> Proposal:
    return container.proposals.reject(proposal_id, note=review.note if review else None)
