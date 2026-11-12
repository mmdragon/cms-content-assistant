from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class EventType(StrEnum):
    TOOL_CALL = "tool_call"
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"
    ERROR = "error"


class Actor(StrEnum):
    ASSISTANT = "assistant"
    EDITOR = "editor"
    SYSTEM = "system"


class ActivityEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    event_type: EventType
    actor: Actor
    tool_name: str | None
    details: dict[str, Any]
    status: str
    created_at: datetime
