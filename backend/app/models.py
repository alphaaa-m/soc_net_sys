"""SQLAlchemy models — one class per table (PRD Part C).

Index strategy: every secondary index is declared explicitly by name in
``__table_args__`` (composite shape follows PRD Part C). Plain ASC btree
indexes serve both ASC and DESC ordering via forward/backward scans, which
keeps ``alembic check`` / ``--autogenerate`` free of phantom diffs.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# PRD requires BIGINT on PostgreSQL, but SQLite only autoincrements columns
# typed exactly INTEGER. This variant gives us both.
PKBigInt = BigInteger().with_variant(Integer(), "sqlite")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(Base, TimestampMixin):
    """users table. Passwords stored as hashes only; email/username lowercase."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    bio: Mapped[str | None] = mapped_column(String(160), nullable=True, default=None)
    role: Mapped[str] = mapped_column(String(10), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (CheckConstraint("role IN ('user','admin')", name="ck_users_role"),)

    posts: Mapped[list["Post"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")


class Follow(Base, TimestampMixin):
    """follows junction table. Composite PK prevents duplicate follows."""

    __tablename__ = "follows"

    follower_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    following_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (
        CheckConstraint("follower_id <> following_id", name="ck_follows_no_self"),
        Index("ix_follows_following_id", "following_id"),
    )


class Post(Base):
    """posts table. Soft delete via deleted_at; reads must filter deleted_at IS NULL."""

    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_posts_author_created", "author_id", "created_at"),
        Index("ix_posts_created", "created_at"),
    )

    author: Mapped["User"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan"
    )


class Comment(Base):
    """comments table. parent_comment_id NULL = top-level; else a one-level reply."""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    parent_comment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    content: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_comments_post_created", "post_id", "created_at"),
        Index("ix_comments_parent", "parent_comment_id"),
    )

    post: Mapped["Post"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")


class PostLike(Base, TimestampMixin):
    """post_likes. Composite PK (user_id, post_id) prevents duplicate likes."""

    __tablename__ = "post_likes"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (Index("ix_post_likes_post_id", "post_id"),)


class CommentLike(Base, TimestampMixin):
    __tablename__ = "comment_likes"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    comment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (Index("ix_comment_likes_comment_id", "comment_id"),)


class Repost(Base, TimestampMixin):
    __tablename__ = "reposts"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    original_post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    quote_text: Mapped[str | None] = mapped_column(String(280), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "original_post_id", name="uq_reposts_user_original"
        ),
        Index("ix_reposts_created", "created_at"),
    )


class Bookmark(Base, TimestampMixin):
    __tablename__ = "bookmarks"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (Index("ix_bookmarks_user_created", "user_id", "created_at"),)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    post_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True
    )
    comment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            "type IN ('follow','post_like','comment','reply','mention')",
            name="ck_notifications_type",
        ),
        Index("ix_notifications_recipient", "recipient_id", "is_read", "created_at"),
    )


class Block(Base, TimestampMixin):
    __tablename__ = "blocks"

    blocker_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    blocked_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (
        CheckConstraint("blocker_id <> blocked_id", name="ck_blocks_no_self"),
        Index("ix_blocks_blocked_id", "blocked_id"),
    )


class Report(Base):
    """reports. Exactly one of reported_user/post/comment must be set (CHECK)."""

    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    reporter_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    reported_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    reported_post_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True
    )
    reported_comment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "reason IN ('spam','harassment','hate','misinformation','other')",
            name="ck_reports_reason",
        ),
        CheckConstraint(
            "status IN ('open','reviewed','dismissed','action_taken')",
            name="ck_reports_status",
        ),
        CheckConstraint(
            "(CASE WHEN reported_user_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN reported_post_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN reported_comment_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_reports_exactly_one_target",
        ),
        Index("ix_reports_status_created", "status", "created_at"),
    )


class Hashtag(Base):
    __tablename__ = "hashtags"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class PostHashtag(Base):
    __tablename__ = "post_hashtags"

    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True
    )
    hashtag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("hashtags.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (Index("ix_post_hashtags_hashtag", "hashtag_id"),)


class Mention(Base, TimestampMixin):
    """mentions. Exactly one of post_id / comment_id must be set (CHECK)."""

    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(PKBigInt, primary_key=True, autoincrement=True)
    mentioned_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True
    )
    comment_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN post_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN comment_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_mentions_exactly_one_target",
        ),
        Index("ix_mentions_user", "mentioned_user_id"),
    )
