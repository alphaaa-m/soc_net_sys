"""Team A — Repost business rules (Phase 3, PRD B8).

A repost is a row pointing at the original post, guarded by
``UNIQUE(user_id, original_post_id)``. Rules:

- missing, soft-deleted or author-deactivated posts -> 404
- reposting your own post -> 403 (PRD policy choice for the repost endpoint)
- duplicate repost -> 409; the database constraint is the real guard, so an
  ``IntegrityError`` from a race is translated to 409
- unreposting is possible; 404 when the repost does not exist
- share counts are computed in one grouped query for a whole page (no N+1)

Blocked-user enforcement is deliberately absent: blocking is Phase 6 and no
approved block service exists yet (PRD B8/B15).
"""

from collections.abc import Iterable

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.exceptions import conflict, forbidden, not_found

POST_NOT_FOUND = "Post not found."
SELF_REPOST = "You cannot repost your own post."
ALREADY_REPOSTED = "You have already reposted this post."
NOT_REPOSTED = "You have not reposted this post."


def _live_post_or_404(db: Session, post_id: int) -> models.Post:
    """Load a repostable post or raise 404 (same visibility rules as likes)."""
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


def repost_post(
    db: Session,
    user: models.User,
    post_id: int,
    quote_text: str | None = None,
) -> models.Repost:
    """Repost someone else's post, optionally with a quote."""
    post = _live_post_or_404(db, post_id)

    if post.author_id == user.id:
        raise forbidden(SELF_REPOST)

    existing = (
        db.query(models.Repost)
        .filter(
            models.Repost.user_id == user.id,
            models.Repost.original_post_id == post_id,
        )
        .first()
    )
    if existing is not None:
        raise conflict(ALREADY_REPOSTED)

    repost = models.Repost(
        user_id=user.id,
        original_post_id=post_id,
        quote_text=quote_text,
    )
    db.add(repost)
    try:
        db.commit()
    except IntegrityError as err:
        # Lost a race on UNIQUE(user_id, original_post_id).
        db.rollback()
        _live_post_or_404(db, post_id)
        raise conflict(ALREADY_REPOSTED) from err

    db.refresh(repost)
    return repost


def unrepost_post(db: Session, user: models.User, post_id: int) -> None:
    """Delete the current user's repost; 404 when it does not exist.

    The original does not need to be visible: if it was soft-deleted between
    the repost and now, the author can still clean up their own repost row.
    """
    repost = (
        db.query(models.Repost)
        .filter(
            models.Repost.user_id == user.id,
            models.Repost.original_post_id == post_id,
        )
        .first()
    )
    if repost is None:
        raise not_found(NOT_REPOSTED)

    db.delete(repost)
    db.commit()


def get_repost_counts(db: Session, post_ids: Iterable[int]) -> dict[int, int]:
    """Return ``{post_id: share_count}`` using a single grouped query.

    Every supplied id is present in the result (``0`` when unreposted), ready
    for the page-level wiring PR without N+1 queries.
    """
    ids = list(dict.fromkeys(post_ids))
    if not ids:
        return {}

    rows = (
        db.query(models.Repost.original_post_id, func.count(models.Repost.id))
        .filter(models.Repost.original_post_id.in_(ids))
        .group_by(models.Repost.original_post_id)
        .all()
    )

    counts = dict.fromkeys(ids, 0)
    counts.update({post_id: int(total) for post_id, total in rows})
    return counts
