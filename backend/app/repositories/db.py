"""Shared SQLite connection handling."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def connect(db_path: str, *, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    """Open a connection that commits on success and rolls back on any exception.

    `immediate=True` takes the write lock up front (BEGIN IMMEDIATE), so read-check-write
    sequences such as approving a proposal cannot interleave with another writer.
    """
    conn = sqlite3.connect(db_path, timeout=5.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
