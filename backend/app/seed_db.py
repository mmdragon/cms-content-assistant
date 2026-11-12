"""Reset the local SQLite database to the seed dataset.

Usage (from backend/):  uv run python -m app.seed_db
This deletes all content, proposals, and activity events in the configured database.
"""

from app.config import get_settings
from app.repositories.sqlite import SQLiteContentRepository
from app.services.seeding import seed_repository


def main() -> None:
    settings = get_settings()
    repo = SQLiteContentRepository(settings.database_path)
    count = seed_repository(repo)
    print(f"Seeded {count} content entries into {settings.database_path}")


if __name__ == "__main__":
    main()
