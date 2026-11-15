"""Team A — Follow system business logic (Phase 2).

All follow rules live here so routers stay thin (PRD Part E):

- cannot follow yourself -> 400
- target missing or deactivated -> 404 (deactivated accounts are hidden
  from public views, consistent with PRD B1/B2)
- duplicate follow -> 409 (also protected by the composite primary key)
- unfollow when not following -> 404
- follower/following lists are public and hide deactivated accounts
- count helpers are ready for the profile wiring PR (user_service.py owner)
"""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.exceptions import conflict, not_found

USER_NOT_FOUND = "User not found."
SELF_FOLLOW = "You cannot follow yourself."
ALREADY_FOLLOWING = "You are already following this user."
NOT_FOLLOWING = "You are not following this user."


def _get_active_user(db: Session, user_id: int) -> models.User:
    """Return an active user or raise the documented 404."""
    user = db.get(models.User, user_id)
    if user is None or not user.is_active:
        raise not_found(USER_NOT_FOUND)
    return user


def _get_active_user_by_username(db: Session, username: str) -> models.User:
    """Case-insensitive public lookup; deactivated users are hidden."""
    user = db.scalar(
        select(models.User).where(
            func.lower(models.User.username) == username.strip().lower(),
            models.User.is_active.is_(True),
        )
    )
    if user is None:
        raise not_found(USER_NOT_FOUND)
    return user


def follow_user(db: Session, follower: models.User, following_id: int) -> models.Follow:
    """Create the follow relationship, enforcing every Phase 2 rule."""
    if follower.id == following_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=SELF_FOLLOW,
        )

    _get_active_user(db, following_id)

    if db.get(models.Follow, (follower.id, following_id)) is not None:
        raise conflict(ALREADY_FOLLOWING)

    follow = models.Follow(follower_id=follower.id, following_id=following_id)
    db.add(follow)
    try:
        db.commit()
    except IntegrityError as err:
        # The composite PK is the real duplicate guard (two requests at once).
        db.rollback()
        if db.get(models.User, following_id) is None:
            raise not_found(USER_NOT_FOUND) from err
        raise conflict(ALREADY_FOLLOWING) from err

    db.refresh(follow)
    return follow


def unfollow_user(db: Session, follower: models.User, following_id: int) -> None:
    """Remove the relationship or return 404 when it does not exist."""
    if db.get(models.User, following_id) is None:
        raise not_found(USER_NOT_FOUND)

    follow = db.get(models.Follow, (follower.id, following_id))
    if follow is None:
        raise not_found(NOT_FOLLOWING)

    db.delete(follow)
    db.commit()


def list_followers(
    db: Session, username: str, limit: int, offset: int
) -> tuple[list[models.User], int]:
    """Return (page of active followers, total active followers)."""
    target = _get_active_user_by_username(db, username)

    page_query = (
        select(models.User)
        .join(models.Follow, models.Follow.follower_id == models.User.id)
        .where(
            models.Follow.following_id == target.id,
            models.User.is_active.is_(True),
        )
        .order_by(models.Follow.created_at.desc(), models.User.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(db.scalars(page_query).all())

    total = db.scalar(
        select(func.count())
        .select_from(models.Follow)
        .join(models.User, models.User.id == models.Follow.follower_id)
        .where(
            models.Follow.following_id == target.id,
            models.User.is_active.is_(True),
        )
    )
    return items, int(total or 0)


def list_following(
    db: Session, username: str, limit: int, offset: int
) -> tuple[list[models.User], int]:
    """Return (page of active followed users, total active followed users)."""
    target = _get_active_user_by_username(db, username)

    page_query = (
        select(models.User)
        .join(models.Follow, models.Follow.following_id == models.User.id)
        .where(
            models.Follow.follower_id == target.id,
            models.User.is_active.is_(True),
        )
        .order_by(models.Follow.created_at.desc(), models.User.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(db.scalars(page_query).all())

    total = db.scalar(
        select(func.count())
        .select_from(models.Follow)
        .join(models.User, models.User.id == models.Follow.following_id)
        .where(
            models.Follow.follower_id == target.id,
            models.User.is_active.is_(True),
        )
    )
    return items, int(total or 0)


def count_followers(db: Session, user_id: int) -> int:
    """Number of active users following ``user_id``.

    Public counts hide deactivated accounts, matching the list endpoints.
    Ready to be wired into the profile response by the user_service owner.
    """
    total = db.scalar(
        select(func.count())
        .select_from(models.Follow)
        .join(models.User, models.User.id == models.Follow.follower_id)
        .where(
            models.Follow.following_id == user_id,
            models.User.is_active.is_(True),
        )
    )
    return int(total or 0)


def count_following(db: Session, user_id: int) -> int:
    """Number of active users that ``user_id`` follows."""
    total = db.scalar(
        select(func.count())
        .select_from(models.Follow)
        .join(models.User, models.User.id == models.Follow.following_id)
        .where(
            models.Follow.follower_id == user_id,
            models.User.is_active.is_(True),
        )
    )
    return int(total or 0)


def is_following(db: Session, follower_id: int, following_id: int) -> bool:
    """Whether ``follower_id`` follows ``following_id`` (profile wiring helper)."""
    return db.get(models.Follow, (follower_id, following_id)) is not None
