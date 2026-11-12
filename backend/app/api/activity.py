from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.api.deps import AppContainer
from app.models.activity import ActivityEvent, EventType

router = APIRouter(tags=["activity"])


class ActivityListResponse(BaseModel):
    items: list[ActivityEvent]
    total: int
    limit: int
    offset: int


@router.get("/activity", response_model=ActivityListResponse)
def list_activity(
    container: AppContainer,
    event_type: EventType | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ActivityListResponse:
    items, total = container.activity_repo.list(limit=limit, offset=offset, event_type=event_type)
    return ActivityListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/tools")
def list_tools(container: AppContainer) -> list[dict[str, Any]]:
    """The agent's tool allowlist with JSON schemas (read-only, for transparency)."""
    return container.tools.describe()
