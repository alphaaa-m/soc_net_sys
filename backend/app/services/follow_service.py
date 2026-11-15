"""Follow-graph business rules (PRD Part D, Phase 2).

A follow is a row in the ``follows`` junction table. The composite primary key
``(follower_id, following_id)`` and the ``CHECK (follower_id <> following_id)``
constraint are the database safety net; this module enforces the same rules in
code so callers get clean 400/404/409 responses instead of IntegrityErrors.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.exceptions import bad_request, conflict, not_found
from app.schemas import follow as follow_schemas
from app.services import user_service


def count_followers(db: Session, user_id: int) -> int:
    """Number of users following ``user_id`` (COUNT(*), PRD MVP)."""
    return db.query(models.Follow).filter(models.Follow.following_id == user_id).count()


def count_following(db: Session, user_id: int) -> int:
    """Number of users ``user_id`` follows."""
    return db.query(models.Follow).filter(models.Follow.follower_id == user_id).count()


def is_following(db: Session, follower_id: int, following_id: int) -> bool:
    """Whether ``follower_id`` currently follows ``following_id``."""
    return (
        db.query(models.Follow)
        .filter(
            models.Follow.follower_id == follower_id,
            models.Follow.following_id == following_id,
        )
        .first()
        is not None
    )


def follow_user(db: Session, follower: models.User, target_id: int) -> None:
    """Create a follow edge. 400 self-follow, 404 missing/deactivated, 409 duplicate."""
    if follower.id == target_id:
        raise bad_request("You cannot follow yourself.")

    # Deactivated users are hidden, so "follow" reports them as not found (PRD).
    target = db.get(models.User, target_id)
    if target is None or not target.is_active:
        raise not_found("User not found.")

    if is_following(db, follower.id, target.id):
        raise conflict("You are already following this user.")

    db.add(models.Follow(follower_id=follower.id, following_id=target.id))
    try:
        db.commit()
    except IntegrityError as err:
        # Lost a race between the check above and the insert; the PK caught it.
        db.rollback()
        raise conflict("You are already following this user.") from err


def unfollow_user(db: Session, follower: models.User, target_id: int) -> None:
    """Remove a follow edge; 404 when the edge does not exist (team decision)."""
    edge = (
        db.query(models.Follow)
        .filter(
            models.Follow.follower_id == follower.id,
            models.Follow.following_id == target_id,
        )
        .first()
    )
    if edge is None:
        raise not_found("You are not following this user.")
    db.delete(edge)
    db.commit()


def _build_page(
    db: Session,
    users: list[models.User],
    *,
    limit: int,
    offset: int,
    total: int,
    current: models.User | None,
) -> follow_schemas.UserPage:
    followed: set[int] = set()
    if current is not None and users:
        ids = [user.id for user in users]
        edges = (
            db.query(models.Follow.following_id)
            .filter(
                models.Follow.follower_id == current.id,
                models.Follow.following_id.in_(ids),
            )
            .all()
        )
        followed = {row[0] for row in edges}

    items = [
        follow_schemas.UserSummary(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            is_following=user.id in followed,
        )
        for user in users
    ]
    return follow_schemas.UserPage(items=items, limit=limit, offset=offset, total=total)


def list_followers(
    db: Session,
    username: str,
    *,
    limit: int,
    offset: int,
    current: models.User | None,
) -> follow_schemas.UserPage:
    """Users who follow ``username``, most recent follows first."""
    user = user_service.get_active_user_by_username(db, username)
    base = (
        db.query(models.User)
        .join(models.Follow, models.Follow.follower_id == models.User.id)
        .filter(
            models.Follow.following_id == user.id,
            models.User.is_active.is_(True),
        )
    )
    total = base.count()
    rows = (
        base.order_by(models.Follow.created_at.desc(), models.User.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return _build_page(
        db, rows, limit=limit, offset=offset, total=total, current=current
    )


def list_following(
    db: Session,
    username: str,
    *,
    limit: int,
    offset: int,
    current: models.User | None,
) -> follow_schemas.UserPage:
    """Users ``username`` follows, most recent follows first."""
    user = user_service.get_active_user_by_username(db, username)
    base = (
        db.query(models.User)
        .join(models.Follow, models.Follow.following_id == models.User.id)
        .filter(
            models.Follow.follower_id == user.id,
            models.User.is_active.is_(True),
        )
    )
    total = base.count()
    rows = (
        base.order_by(models.Follow.created_at.desc(), models.User.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return _build_page(
        db, rows, limit=limit, offset=offset, total=total, current=current
    )
