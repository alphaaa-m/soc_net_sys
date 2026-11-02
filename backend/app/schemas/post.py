"""Post request/response schemas (PRD Part D, Phase 2).

``like_count`` / ``comment_count`` / ``share_count`` are stubbed to ``0`` in
Phase 2 (the stub-and-wire pattern); Phases 3-4 plug in the real bulk queries.
The response *shape* is final so the frontend can be built against it now.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_content(value: object) -> object:
    if isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("Content cannot be empty.")
    return value


class PostCreate(BaseModel):
    """Body for ``POST /posts`` (trimmed, non-empty, <= 280 chars)."""

    content: str = Field(min_length=1, max_length=280)

    @field_validator("content", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return _clean_content(value)


class PostUpdate(BaseModel):
    """Body for ``PATCH /posts/{post_id}``."""

    content: str = Field(min_length=1, max_length=280)

    @field_validator("content", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return _clean_content(value)


class PostAuthor(BaseModel):
    """The slim author object embedded in every post (PRD response standard)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str


class PostRead(BaseModel):
    """A post exactly as the API returns it everywhere (PRD Part D)."""

    id: int
    content: str
    author: PostAuthor
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    liked_by_me: bool = False
    bookmarked_by_me: bool = False
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class PostPage(BaseModel):
    """Paginated post list (PRD response standard)."""

    items: list[PostRead]
    limit: int
    offset: int
    total: int
