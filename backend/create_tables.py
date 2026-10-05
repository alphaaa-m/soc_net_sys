"""Create all tables directly from SQLAlchemy models (dev shortcut).

COMMANDS (run from the ``backend/`` folder, all via ``uv run``):

  Create tables (database from .env DATABASE_URL):
    uv run python create_tables.py
    uv run python create_tables.py --url "postgresql+psycopg2://u:p@localhost:5432/CHIRP"

  Drop + recreate (DESTROYS data):
    uv run python create_tables.py --drop

  Migrations (versioned, team workflow — PREFERRED):
    uv run alembic upgrade head          # apply all migrations (create tables)
    uv run alembic downgrade base        # drop all versioned tables
    uv run alembic revision --autogenerate -m "add xyz"   # new migration
    uv run alembic history               # list migrations
    uv run alembic current               # show current DB revision

NOTE: create_tables.py does NOT use the migration history. Teams must use
alembic commands so every database stays in sync (PRD Part C).
"""

import argparse
import sys

sys.path.insert(0, ".")

from sqlalchemy import create_engine  # noqa: E402

import app.models  # noqa: F401  (import registers all tables on Base)
from app.config import get_settings  # noqa: E402
from app.database import Base  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Chirp tables (dev shortcut).")
    parser.add_argument(
        "--url", default=None, help="SQLAlchemy URL (default: DATABASE_URL from .env)"
    )
    parser.add_argument("--drop", action="store_true", help="Drop all tables first (DESTROYS data)")
    args = parser.parse_args()

    url = args.url or get_settings().DATABASE_URL
    # Hide password in logs
    safe = url.split("@")[-1] if "@" in url else url
    print(f"Target: ...@{safe}")

    engine = create_engine(url)
    if args.drop:
        confirm = input("Drop ALL tables? Type DROP to confirm: ")
        if confirm != "DROP":
            print("Aborted.")
            return
        Base.metadata.drop_all(engine)
        print("Dropped all tables.")

    Base.metadata.create_all(engine)
    print(f"Created {len(Base.metadata.tables)} tables: {', '.join(sorted(Base.metadata.tables))}")


if __name__ == "__main__":
    main()
