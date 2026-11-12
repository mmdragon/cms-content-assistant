from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query

from app.api.deps import ContentRepo
from app.models.content import CONTENT_ID_PATTERN, ContentEntry, ContentSummary
from app.repositories.base import ContentQuery
from app.schemas.content import ContentListResponse

router = APIRouter(prefix="/content", tags=["content"])


@router.get("", response_model=ContentListResponse)
def list_content(
    repo: ContentRepo,
    query: Annotated[ContentQuery, Query()],
) -> ContentListResponse:
    page = repo.list_content(query)
    return ContentListResponse(
        items=[ContentSummary.from_entry(e) for e in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{content_id}", response_model=ContentEntry)
def get_content(
    repo: ContentRepo,
    content_id: Annotated[str, Path(pattern=CONTENT_ID_PATTERN)],
) -> ContentEntry:
    entry = repo.get_content(content_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Content '{content_id}' not found")
    return entry
