"""Profile business rules (PRD B2).

Counts are computed live from the database rather than stored as counters, so
they can never drift (PRD B3). Deactivated users are hidden from public views.
"""

from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.exceptions import not_found
from app.schemas import user as user_schemas


def get_active_user_by_username(db: Session, username: str) -> models.User:
    """Fetch an active user by (case-insensitive) username or raise 404."""
    user = (
        db.query(models.User)
        .filter(
            models.User.username == username.strip().lower(),
            models.User.is_active.is_(True),
        )
        .first()
    )
    if user is None:
        raise not_found("User not found.")
    return user


def _counts(db: Session, user_id: int) -> tuple[int, int, int]:
    followers = (
        db.query(func.count())
        .select_from(models.Follow)
        .filter(models.Follow.following_id == user_id)
        .scalar()
    ) or 0
    following = (
        db.query(func.count())
        .select_from(models.Follow)
        .filter(models.Follow.follower_id == user_id)
        .scalar()
    ) or 0
    posts = (
        db.query(func.count())
        .select_from(models.Post)
        .filter(models.Post.author_id == user_id, models.Post.deleted_at.is_(None))
        .scalar()
    ) or 0
    return followers, following, posts


def _is_following(db: Session, follower_id: int, following_id: int) -> bool:
    return (
        db.query(models.Follow)
        .filter(
            models.Follow.follower_id == follower_id,
            models.Follow.following_id == following_id,
        )
        .first()
        is not None
    )


def build_profile(
    db: Session,
    target: models.User,
    current: models.User | None,
) -> user_schemas.UserProfile:
    """Assemble a public profile, personalised when a caller is logged in."""
    followers, following, posts = _counts(db, target.id)
    return user_schemas.UserProfile(
        id=target.id,
        username=target.username,
        display_name=target.display_name,
        bio=target.bio,
        created_at=target.created_at,
        followers_count=followers,
        following_count=following,
        posts_count=posts,
        is_following=bool(current and _is_following(db, current.id, target.id)),
    )


def get_profile(
    db: Session,
    username: str,
    current: models.User | None,
) -> user_schemas.UserProfile:
    target = get_active_user_by_username(db, username)
    return build_profile(db, target, current)


def update_profile(db: Session, user: models.User, changes: dict) -> models.User:
    """Apply a partial update from ``UserUpdate`` (only set fields change)."""
    if changes.get("display_name") is not None:
        user.display_name = changes["display_name"]
    if "bio" in changes:
        user.bio = changes["bio"]
    user.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user
