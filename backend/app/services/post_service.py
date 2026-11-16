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
from app.services import like_service, repost_service, user_service


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


def _to_read(
    post: models.Post,
    *,
    like_count: int = 0,
    share_count: int = 0,
    liked_by_me: bool = False,
) -> post_schemas.PostRead:
    """Map a model to the public post shape.

    ``comment_count`` remains stubbed until Phase 3 Team B's wiring PR; the
    like/share counts and ``liked_by_me`` are filled by ``_read_many`` below.
    """
    return post_schemas.PostRead(
        id=post.id,
        content=post.content,
        author=post_schemas.PostAuthor.model_validate(post.author),
        like_count=like_count,
        share_count=share_count,
        liked_by_me=liked_by_me,
        is_edited=post.updated_at is not None,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


def _read_many(
    db: Session,
    posts: list[models.Post],
    current: models.User | None,
) -> list[post_schemas.PostRead]:
    """Serialise a page of posts with one grouped query per interaction type.

    Keeping the counts in bulk helpers avoids N+1 queries (PM Plan Phase 3
    review checklist).
    """
    ids = [post.id for post in posts]
    like_counts = like_service.get_like_counts(db, ids)
    share_counts = repost_service.get_repost_counts(db, ids)
    liked = like_service.liked_post_ids(db, current.id, ids) if current else set()

    return [
        _to_read(
            post,
            like_count=like_counts.get(post.id, 0),
            share_count=share_counts.get(post.id, 0),
            liked_by_me=post.id in liked,
        )
        for post in posts
    ]


def create_post(db: Session, author: models.User, content: str) -> post_schemas.PostRead:
    post = models.Post(author_id=author.id, content=content)
    db.add(post)
    db.commit()
    db.refresh(post)
    return _to_read(post)


def get_post(
    db: Session,
    post_id: int,
    current: models.User | None = None,
) -> post_schemas.PostRead:
    post = _post_or_404(db, post_id)
    return _read_many(db, [post], current)[0]


def list_user_posts(
    db: Session,
    username: str,
    *,
    limit: int,
    offset: int,
    current: models.User | None = None,
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
        items=_read_many(db, posts, current),
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
    return _read_many(db, [post], current)[0]


def delete_post(db: Session, post_id: int, current: models.User) -> None:
    """Soft-delete a post; the author or an admin may delete it."""
    post = db.get(models.Post, post_id)
    if post is None or post.deleted_at is not None:
        raise not_found("Post not found.")
    if post.author_id != current.id and current.role != "admin":
        raise forbidden("You can only delete your own posts.")

    post.deleted_at = datetime.now(UTC)
    db.commit()
