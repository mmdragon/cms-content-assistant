"""Load the fictional Northstar Living seed dataset into a repository."""

import json
from pathlib import Path

from pydantic import TypeAdapter

from app.models.content import ContentEntry
from app.repositories.sqlite import SQLiteContentRepository

SEED_FILE = Path(__file__).resolve().parents[2] / "seed" / "content.json"

_entries_adapter = TypeAdapter(list[ContentEntry])


def load_seed_entries(path: Path = SEED_FILE) -> list[ContentEntry]:
    """Parse and validate the seed file. Raises ValueError on duplicate ids or slugs."""
    entries = _entries_adapter.validate_python(json.loads(path.read_text(encoding="utf-8")))
    for field in ("id", "slug"):
        values = [getattr(e, field) for e in entries]
        dupes = sorted({v for v in values if values.count(v) > 1})
        if dupes:
            raise ValueError(f"duplicate {field} values in seed data: {dupes}")
    return entries


def seed_repository(repo: SQLiteContentRepository, path: Path = SEED_FILE) -> int:
    repo.init_schema()
    return repo.replace_all(load_seed_entries(path))


def ensure_seeded(repo: SQLiteContentRepository, path: Path = SEED_FILE) -> int:
    """Create the schema and seed it only if the content table is empty. Returns rows inserted."""
    repo.init_schema()
    if repo.count() > 0:
        return 0
    return repo.replace_all(load_seed_entries(path))
