"""Post business rules (PRD Part D, Phase 2).

Posts are **soft deleted** (``deleted_at``) so the row survives for moderation
and history; every read filters ``deleted_at IS NULL``. Only the author may
edit/delete; admins may also delete (PRD permissions).
"""

from datetime import UTC, datetime

from sqlalchemy.orm import Session, joinedload

from app import models
from app.exceptions import forbidden, not_found
from app.schemas import post as post_schemas
from app.services import user_service


def count_user_posts(db: Session, user_id: int) -> int:
    """Non-deleted posts authored by ``user_id`` (used by the profile counts)."""
    return (
        db.query(models.Post)
        .filter(models.Post.author_id == user_id, models.Post.deleted_at.is_(None))
        .count()
    )


def _post_or_404(db: Session, post_id: int) -> models.Post:
    """Load a live post (and its author) or raise 404.

    Soft-deleted posts and posts by deactivated authors are treated as missing.
    """
    post = (
        db.query(models.Post)
        .options(joinedload(models.Post.author))
        .filter(models.Post.id == post_id, models.Post.deleted_at.is_(None))
        .first()
    )
    if post is None or not post.author.is_active:
        raise not_found("Post not found.")
    return post


def _to_read(post: models.Post) -> post_schemas.PostRead:
    """Map a model to the public post shape.

    Counts and per-viewer flags stay at their schema defaults until the Phase 3
    wiring PRs plug in the bulk queries (stub-and-wire).
    """
    return post_schemas.PostRead(
        id=post.id,
        content=post.content,
        author=post_schemas.PostAuthor.model_validate(post.author),
        is_edited=post.updated_at is not None,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def create_post(db: Session, author: models.User, content: str) -> post_schemas.PostRead:
    post = models.Post(author_id=author.id, content=content)
    db.add(post)
    db.commit()
    db.refresh(post)
    return _to_read(post)


def get_post(db: Session, post_id: int) -> post_schemas.PostRead:
    return _to_read(_post_or_404(db, post_id))


def list_user_posts(
    db: Session,
    username: str,
    *,
    limit: int,
    offset: int,
) -> post_schemas.PostPage:
    """Personal posts, newest first (``created_at DESC, id DESC`` for stability)."""
    author = user_service.get_active_user_by_username(db, username)
    base = (
        db.query(models.Post)
        .options(joinedload(models.Post.author))
        .filter(
            models.Post.author_id == author.id,
            models.Post.deleted_at.is_(None),
        )
    )
    total = base.count()
    posts = (
        base.order_by(models.Post.created_at.desc(), models.Post.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return post_schemas.PostPage(
        items=[_to_read(post) for post in posts],
        limit=limit,
        offset=offset,
        total=total,
    )


def update_post(
    db: Session,
    post_id: int,
    current: models.User,
    content: str,
) -> post_schemas.PostRead:
    """Edit a post; only the author may do so (403 otherwise, 404 if gone)."""
    post = db.get(models.Post, post_id)
    if post is None or post.deleted_at is not None:
        raise not_found("Post not found.")
    if post.author_id != current.id:
        raise forbidden("You can only edit your own posts.")

    post.content = content
    post.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(post)
    return _to_read(post)


def delete_post(db: Session, post_id: int, current: models.User) -> None:
    """Soft-delete a post; the author or an admin may delete it."""
    post = db.get(models.Post, post_id)
    if post is None or post.deleted_at is not None:
        raise not_found("Post not found.")
    if post.author_id != current.id and current.role != "admin":
        raise forbidden("You can only delete your own posts.")

    post.deleted_at = datetime.now(UTC)
    db.commit()
