"""SQLite implementation of the content repository.

All SQL lives here. Every query is parameterized; the only dynamic SQL fragments
(ORDER BY clauses) come from a fixed allowlist keyed by an enum.
"""

import json
import sqlite3
from collections.abc import Iterable, Iterator, Sequence
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.content import ContentEntry
from app.repositories.base import ContentPage, ContentQuery, ContentSort

SCHEMA = """
CREATE TABLE IF NOT EXISTS content_entries (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    slug             TEXT NOT NULL UNIQUE,
    content          TEXT NOT NULL,
    category         TEXT NOT NULL,
    status           TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    meta_title       TEXT,
    meta_description TEXT,
    canonical_url    TEXT,
    tags_json        TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_content_category ON content_entries(category);
CREATE INDEX IF NOT EXISTS idx_content_status ON content_entries(status);
CREATE INDEX IF NOT EXISTS idx_content_updated ON content_entries(updated_at);

CREATE TABLE IF NOT EXISTS proposals (
    id               TEXT PRIMARY KEY,
    content_id       TEXT NOT NULL REFERENCES content_entries(id),
    field_name       TEXT NOT NULL,
    original_value   TEXT,
    proposed_value   TEXT NOT NULL,
    rationale        TEXT NOT NULL,
    evidence_excerpt TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at       TEXT NOT NULL,
    reviewed_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);

CREATE TABLE IF NOT EXISTS activity_events (
    id           TEXT PRIMARY KEY,
    event_type   TEXT NOT NULL,
    actor        TEXT NOT NULL,
    tool_name    TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    status       TEXT NOT NULL,
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity_events(created_at);
"""

_ORDER_BY: dict[ContentSort, str] = {
    ContentSort.UPDATED_DESC: "updated_at DESC, id ASC",
    ContentSort.UPDATED_ASC: "updated_at ASC, id ASC",
    ContentSort.TITLE_ASC: "title COLLATE NOCASE ASC, id ASC",
}

_COLUMNS = (
    "id, title, slug, content, category, status, created_at, updated_at, "
    "meta_title, meta_description, canonical_url, tags_json"
)


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _to_db_time(value: datetime) -> str:
    return value.isoformat()


def _row_to_entry(row: sqlite3.Row) -> ContentEntry:
    data: dict[str, Any] = dict(row)
    data["tags"] = json.loads(data.pop("tags_json"))
    return ContentEntry.model_validate(data)


class SQLiteContentRepository:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---- setup -------------------------------------------------------------

    def init_schema(self) -> None:
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def replace_all(self, entries: Iterable[ContentEntry]) -> int:
        """Delete all content (and dependent rows) and insert `entries`. Used for seeding only."""
        rows = [
            (
                e.id,
                e.title,
                e.slug,
                e.content,
                e.category.value,
                e.status.value,
                _to_db_time(e.created_at),
                _to_db_time(e.updated_at),
                e.meta_title,
                e.meta_description,
                e.canonical_url,
                json.dumps(e.tags),
            )
            for e in entries
        ]
        with self._connect() as conn:
            conn.execute("DELETE FROM proposals")
            conn.execute("DELETE FROM activity_events")
            conn.execute("DELETE FROM content_entries")
            conn.executemany(
                f"INSERT INTO content_entries ({_COLUMNS}) "  # noqa: S608 - constant column list
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows,
            )
        return len(rows)

    # ---- reads -------------------------------------------------------------

    def list_content(self, query: ContentQuery) -> ContentPage:
        clauses: list[str] = []
        params: list[Any] = []

        if query.q and query.q.strip():
            pattern = f"%{_escape_like(query.q.strip())}%"
            searchable = ("title", "content", "meta_title", "meta_description", "tags_json")
            clauses.append(
                "(" + " OR ".join(f"COALESCE({c}, '') LIKE ? ESCAPE '\\'" for c in searchable) + ")"
            )
            params.extend([pattern] * len(searchable))
        if query.category is not None:
            clauses.append("category = ?")
            params.append(query.category.value)
        if query.status is not None:
            clauses.append("status = ?")
            params.append(query.status.value)
        if query.tag:
            clauses.append(
                "EXISTS (SELECT 1 FROM json_each(content_entries.tags_json) "
                "WHERE lower(json_each.value) = lower(?))"
            )
            params.append(query.tag)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        order_by = _ORDER_BY[query.sort]

        with self._connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM content_entries {where}",  # noqa: S608 - fixed fragments
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM content_entries {where} "  # noqa: S608 - fixed fragments
                f"ORDER BY {order_by} LIMIT ? OFFSET ?",
                [*params, query.limit, query.offset],
            ).fetchall()

        return ContentPage(
            items=[_row_to_entry(r) for r in rows],
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    def get_content(self, content_id: str) -> ContentEntry | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM content_entries WHERE id = ?",  # noqa: S608
                (content_id,),
            ).fetchone()
        return _row_to_entry(row) if row else None

    def get_by_slug(self, slug: str) -> ContentEntry | None:
        with self._connect() as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM content_entries WHERE slug = ?",  # noqa: S608
                (slug.strip("/"),),
            ).fetchone()
        return _row_to_entry(row) if row else None

    def all_content(self) -> Sequence[ContentEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM content_entries ORDER BY id",  # noqa: S608
            ).fetchall()
        return [_row_to_entry(r) for r in rows]

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM content_entries").fetchone()[0])
