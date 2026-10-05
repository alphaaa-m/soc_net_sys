"""Seed script: create the FIRST admin user + a few demo users (CLI only).

Usage (from backend/):
  uv run python -m scripts.seed --email admin@chirp.local --username admin \
      --password "change-me-123" --admin
  uv run python -m scripts.seed --demo   # admin + 2 demo users + posts

The first admin is NEVER created via a public endpoint (PRD B17).
"""

import argparse
import sys

sys.path.insert(0, ".")

from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: F401  (import registers all tables on Base)
from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import Post, User  # noqa: E402
from app.security import get_password_hash  # noqa: E402


def get_or_create_user(db: Session, *, email: str, username: str, password: str,
                       display_name: str, role: str = "user") -> User:
    email, username = email.lower(), username.lower()
    user = db.query(User).filter((User.email == email) | (User.username == username)).first()
    if user:
        print(f"Exists: {user.username} ({user.email})")
        return user
    user = User(
        email=email, username=username, password_hash=get_password_hash(password),
        display_name=display_name, role=role, is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created [{role}]: {username} ({email})")
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Chirp admin/demo data.")
    parser.add_argument("--email", default="admin@chirp.local")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="change-me-123")
    parser.add_argument("--admin", action="store_true", help="Give the user the admin role")
    parser.add_argument("--demo", action="store_true", help="Also create demo users + posts")
    args = parser.parse_args()

    print(f"DB: {get_settings().DATABASE_URL.split('@')[-1]}")
    db = SessionLocal()
    try:
        get_or_create_user(
            db, email=args.email, username=args.username, password=args.password,
            display_name="Chirp Admin", role="admin" if (args.admin or args.demo) else "user",
        )
        if args.demo:
            a = get_or_create_user(db, email="ali@chirp.local", username="ali",
                                   password="password123", display_name="Ali")
            b = get_or_create_user(db, email="sara@chirp.local", username="sara",
                                   password="password123", display_name="Sara")
            for author, text in [(a, "Learning FastAPI today! #python"), (b, "Hello Chirp @ali")]:
                db.add(Post(author_id=author.id, content=text))
            db.commit()
            print("Demo posts created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
