"""Business logic for user profile operations."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


def get_public_user(db: Session, username: str) -> models.User | None:
    """Return an active user by username; deactivated accounts are not public."""
    statement = select(models.User).where(
        models.User.username == username.lower(),
        models.User.is_active.is_(True),
    )
    return db.scalar(statement)


def update_profile(
    db: Session,
    user: models.User,
    changes: dict[str, str | None],
) -> models.User:
    """Apply validated profile fields and persist the current user's changes."""
    for field, value in changes.items():
        setattr(user, field, value)
    user.updated_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
