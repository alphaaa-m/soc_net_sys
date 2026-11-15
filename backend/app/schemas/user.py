"""User / profile schemas (PRD B2).

``UserPublic`` is what strangers see, ``UserMe`` adds the owner's private
fields (email, role, is_active) and ``UserProfile`` adds the context-sensitive
``is_following`` flag. None of them ever expose ``password_hash``.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserPublic(BaseModel):
    """Public identity + live counts (PRD B2)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    bio: str | None = None
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0


class UserProfile(UserPublic):
    """``UserPublic`` plus whether the *current* caller follows this user."""

    is_following: bool = False


class UserMe(BaseModel):
    """The authenticated user's own account (includes private fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    display_name: str
    bio: str | None = None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Body for ``PATCH /users/me`` — only these fields are editable."""

    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    bio: str | None = Field(default=None, max_length=160)
