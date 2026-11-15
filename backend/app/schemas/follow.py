"""Team A — Follow system schemas (Phase 2).

Response shapes for the follow endpoints (PRD Parts B3 + D). List responses
use the project-wide pagination envelope: ``items``, ``limit``, ``offset``,
``total`` (PRD "Paginated list").
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FollowRead(BaseModel):
    """Representation of the relationship created by PUT /users/{id}/follow."""

    model_config = ConfigDict(from_attributes=True)

    follower_id: int
    following_id: int
    created_at: datetime


class FollowUserRead(BaseModel):
    """Public user summary returned by follower/following lists.

    Deliberately excludes email, password_hash, role and is_active
    (PRD Part B2 public API table).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    bio: str | None = None
    created_at: datetime


class FollowList(BaseModel):
    """Paginated list envelope (PRD API Response Standards)."""

    items: list[FollowUserRead]
    limit: int
    offset: int
    total: int
