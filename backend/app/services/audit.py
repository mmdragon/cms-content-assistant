"""Activity logging with secret redaction and size limits."""

import re
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.models.activity import ActivityEvent, Actor, EventType
from app.repositories.activity import SQLiteActivityRepository

REDACTED = "[REDACTED]"
_SECRET_KEY = re.compile(r"(api[_-]?key|token|secret|password|passwd|authorization|cookie)", re.I)
# Values that look like credentials even under an innocent key name.
_SECRET_VALUE = re.compile(r"(sk-[A-Za-z0-9_-]{16,}|Bearer\s+\S+)")
MAX_LOGGED_STRING = 500
MAX_LOGGED_ITEMS = 50

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def redact(value: Any, *, _depth: int = 0) -> Any:
    """Return a copy of `value` safe to log: secrets masked, long strings and lists truncated."""
    if _depth > 6:
        return "[…]"
    if isinstance(value, dict):
        return {
            str(k): REDACTED if _SECRET_KEY.search(str(k)) else redact(v, _depth=_depth + 1)
            for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        items = [redact(v, _depth=_depth + 1) for v in value[:MAX_LOGGED_ITEMS]]
        if len(value) > MAX_LOGGED_ITEMS:
            items.append(f"[… {len(value) - MAX_LOGGED_ITEMS} more]")
        return items
    if isinstance(value, str):
        masked = _SECRET_VALUE.sub(REDACTED, value)
        if len(masked) > MAX_LOGGED_STRING:
            return (
                masked[:MAX_LOGGED_STRING]
                + f"… [{len(masked) - MAX_LOGGED_STRING} chars truncated]"
            )
        return masked
    return value


class AuditService:
    def __init__(self, repo: SQLiteActivityRepository, clock: Clock = utc_now) -> None:
        self._repo = repo
        self._clock = clock

    def record(
        self,
        event_type: EventType,
        *,
        actor: Actor,
        status: str,
        tool_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            id=f"evt-{uuid.uuid4().hex[:16]}",
            event_type=event_type,
            actor=actor,
            tool_name=tool_name,
            details=redact(details or {}),
            status=status,
            created_at=self._clock(),
        )
        self._repo.add(event)
        return event
