"""SQLite storage for edit proposals, including the one code path that writes content.

`approve_and_apply` is the only place in the application that modifies a content entry.
It is reachable from the human-only approval endpoint, never from an agent tool.
"""

import sqlite3
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.models.proposal import EditableField, Proposal, ProposalStatus
from app.repositories.db import connect

_COLUMNS = (
    "id, content_id, field_name, original_value, proposed_value, rationale, "
    "evidence_excerpt, status, created_at, reviewed_at, review_note"
)

# Allowlisted column names for the content update. Never interpolate anything else.
_CONTENT_COLUMN: dict[EditableField, str] = {
    EditableField.TITLE: "title",
    EditableField.CONTENT: "content",
    EditableField.META_TITLE: "meta_title",
    EditableField.META_DESCRIPTION: "meta_description",
}


class ApplyOutcome(StrEnum):
    APPLIED = "applied"
    NOT_FOUND = "not_found"
    NOT_PENDING = "not_pending"
    CONTENT_CHANGED = "content_changed"  # the field no longer matches original_value


def _row_to_proposal(row: sqlite3.Row) -> Proposal:
    return Proposal.model_validate(dict(row))


class SQLiteProposalRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    def add(self, proposal: Proposal) -> None:
        with connect(self._db_path) as conn:
            conn.execute(
                f"INSERT INTO proposals ({_COLUMNS}) "  # noqa: S608 - constant columns
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    proposal.id,
                    proposal.content_id,
                    proposal.field_name.value,
                    proposal.original_value,
                    proposal.proposed_value,
                    proposal.rationale,
                    proposal.evidence_excerpt,
                    proposal.status.value,
                    proposal.created_at.isoformat(),
                    proposal.reviewed_at.isoformat() if proposal.reviewed_at else None,
                    proposal.review_note,
                ),
            )

    def get(self, proposal_id: str) -> Proposal | None:
        with connect(self._db_path) as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM proposals WHERE id = ?",  # noqa: S608
                (proposal_id,),
            ).fetchone()
        return _row_to_proposal(row) if row else None

    def list(
        self,
        *,
        status: ProposalStatus | None = None,
        content_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Proposal], int]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status = ?")
            params.append(status.value)
        if content_id is not None:
            clauses.append("content_id = ?")
            params.append(content_id)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect(self._db_path) as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM proposals {where}",  # noqa: S608 - fixed fragments
                params,
            ).fetchone()[0]
            rows = conn.execute(
                f"SELECT {_COLUMNS} FROM proposals {where} "  # noqa: S608 - fixed fragments
                "ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return [_row_to_proposal(r) for r in rows], int(total)

    def find_pending(self, content_id: str, field_name: EditableField) -> Proposal | None:
        with connect(self._db_path) as conn:
            row = conn.execute(
                f"SELECT {_COLUMNS} FROM proposals "  # noqa: S608
                "WHERE content_id = ? AND field_name = ? AND status = 'pending' LIMIT 1",
                (content_id, field_name.value),
            ).fetchone()
        return _row_to_proposal(row) if row else None

    def reject(self, proposal_id: str, reviewed_at: datetime, note: str | None) -> ApplyOutcome:
        with connect(self._db_path, immediate=True) as conn:
            row = conn.execute(
                "SELECT status FROM proposals WHERE id = ?", (proposal_id,)
            ).fetchone()
            if row is None:
                return ApplyOutcome.NOT_FOUND
            if row["status"] != ProposalStatus.PENDING:
                return ApplyOutcome.NOT_PENDING
            conn.execute(
                "UPDATE proposals SET status = 'rejected', reviewed_at = ?, review_note = ? "
                "WHERE id = ? AND status = 'pending'",
                (reviewed_at.isoformat(), note, proposal_id),
            )
        return ApplyOutcome.APPLIED

    def approve_and_apply(
        self, proposal_id: str, reviewed_at: datetime, note: str | None
    ) -> ApplyOutcome:
        """Atomically mark a pending proposal approved and write its value to the content entry.

        Uses compare-and-set: the content field must still equal the proposal's original_value,
        so approving a proposal can never overwrite an edit made after the proposal was drafted.
        """
        with connect(self._db_path, immediate=True) as conn:
            row = conn.execute(
                "SELECT content_id, field_name, original_value, proposed_value, status "
                "FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
            if row is None:
                return ApplyOutcome.NOT_FOUND
            if row["status"] != ProposalStatus.PENDING:
                return ApplyOutcome.NOT_PENDING

            column = _CONTENT_COLUMN[EditableField(row["field_name"])]
            updated = conn.execute(
                f"UPDATE content_entries SET {column} = ?, updated_at = ? "  # noqa: S608 - allowlisted column
                f"WHERE id = ? AND {column} IS ?",
                (
                    row["proposed_value"],
                    reviewed_at.isoformat(),
                    row["content_id"],
                    row["original_value"],
                ),
            ).rowcount
            if updated != 1:
                return ApplyOutcome.CONTENT_CHANGED

            conn.execute(
                "UPDATE proposals SET status = 'approved', reviewed_at = ?, review_note = ? "
                "WHERE id = ? AND status = 'pending'",
                (reviewed_at.isoformat(), note, proposal_id),
            )
        return ApplyOutcome.APPLIED
