"""Team A — Post-like business rules (Phase 3, PRD B7).

All like rules live here so routers stay thin (PRD Part E):

- only an authenticated user can like (enforced by the router dependency)
- missing, soft-deleted or author-deactivated posts -> 404
- duplicate like -> 409; the composite primary key is the real guard, so an
  ``IntegrityError`` from two simultaneous requests is translated to 409
- unlike when not liked -> 404
- counts are computed in one grouped query for a whole page of posts (no N+1)
"""

from collections.abc import Iterable

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.exceptions import conflict, not_found

POST_NOT_FOUND = "Post not found."
ALREADY_LIKED = "You have already liked this post."
NOT_LIKED = "You have not liked this post."


def _live_post_or_404(db: Session, post_id: int) -> models.Post:
    """Load a likeable post or raise 404.

    Soft-deleted posts and posts whose author was deactivated are hidden from
    every public view (PRD B4), so they cannot be liked either.
    """
    post = (
        db.query(models.Post)
        .join(models.User, models.User.id == models.Post.author_id)
        .filter(
            models.Post.id == post_id,
            models.Post.deleted_at.is_(None),
            models.User.is_active.is_(True),
        )
        .first()
    )
    if post is None:
        raise not_found(POST_NOT_FOUND)
    return post


def like_post(db: Session, user: models.User, post_id: int) -> models.PostLike:
    """Like a post, or raise 409 when the like already exists."""
    _live_post_or_404(db, post_id)

    if db.get(models.PostLike, (user.id, post_id)) is not None:
        raise conflict(ALREADY_LIKED)

    like = models.PostLike(user_id=user.id, post_id=post_id)
    db.add(like)
    try:
        db.commit()
    except IntegrityError as err:
        # Lost a race between the check and the insert; the composite PK won.
        db.rollback()
        _live_post_or_404(db, post_id)
        raise conflict(ALREADY_LIKED) from err

    db.refresh(like)
    return like


def unlike_post(db: Session, user: models.User, post_id: int) -> None:
    """Remove a like; 404 when the post is gone or was never liked."""
    _live_post_or_404(db, post_id)

    like = db.get(models.PostLike, (user.id, post_id))
    if like is None:
        raise not_found(NOT_LIKED)

    db.delete(like)
    db.commit()


def get_like_counts(db: Session, post_ids: Iterable[int]) -> dict[int, int]:
    """Return ``{post_id: like_count}`` using a single grouped query.

    Every supplied id is present in the result (``0`` when it has no likes),
    which makes the helper convenient for page-level wiring without N+1
    queries.
    """
    ids = list(dict.fromkeys(post_ids))
    if not ids:
        return {}

    rows = (
        db.query(models.PostLike.post_id, func.count(models.PostLike.user_id))
        .filter(models.PostLike.post_id.in_(ids))
        .group_by(models.PostLike.post_id)
        .all()
    )

    counts = dict.fromkeys(ids, 0)
    counts.update({post_id: int(total) for post_id, total in rows})
    return counts


def liked_post_ids(
    db: Session,
    user_id: int,
    post_ids: Iterable[int],
) -> set[int]:
    """Subset of ``post_ids`` the given user has liked (one query).

    Used by the separate wiring PR to fill ``PostRead.liked_by_me``.
    """
    ids = list(dict.fromkeys(post_ids))
    if not ids:
        return set()

    rows = (
        db.query(models.PostLike.post_id)
        .filter(
            models.PostLike.user_id == user_id,
            models.PostLike.post_id.in_(ids),
        )
        .all()
    )
    return {post_id for (post_id,) in rows}
