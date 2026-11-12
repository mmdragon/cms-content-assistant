import json
import sqlite3
from typing import Any

from app.models.activity import ActivityEvent, EventType
from app.repositories.db import connect


def _row_to_event(row: sqlite3.Row) -> ActivityEvent:
    data: dict[str, Any] = dict(row)
    data["details"] = json.loads(data.pop("details_json"))
    return ActivityEvent.model_validate(data)


class SQLiteActivityRepository:
    """Append-only activity log."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def add(self, event: ActivityEvent) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                "INSERT INTO activity_events "
                "(id, event_type, actor, tool_name, details_json, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    event.id,
                    event.event_type.value,
                    event.actor.value,
                    event.tool_name,
                    json.dumps(event.details, default=str),
                    event.status,
                    event.created_at.isoformat(),
                ),
            )

    def list(
        self, *, limit: int = 50, offset: int = 0, event_type: EventType | None = None
    ) -> tuple[list[ActivityEvent], int]:
        where, params = ("WHERE event_type = ?", [event_type.value]) if event_type else ("", [])
        with connect(self._db_path) as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM activity_events {where}",  # noqa: S608 - fixed fragment
                params,
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT id, event_type, actor, tool_name, details_json, status, created_at "  # noqa: S608 - fixed fragment
                f"FROM activity_events {where} "
                "ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return [_row_to_event(r) for r in rows], int(total)
