"""Repost schemas (PRD B8, Phase 3 — Team A).

A repost references the original post instead of copying it, so edits and
deletions propagate and attribution is preserved. Quote text is optional and
capped at 280 characters like a post body.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RepostCreate(BaseModel):
    """Body for ``POST /posts/{post_id}/repost`` (optional quote text)."""

    quote_text: str | None = Field(default=None, max_length=280)

    @field_validator("quote_text", mode="before")
    @classmethod
    def _strip_blank(cls, value: object) -> object:
        """Trim surrounding whitespace; an empty quote means "no quote"."""
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class RepostRead(BaseModel):
    """The repost created by ``POST /posts/{post_id}/repost``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    original_post_id: int
    quote_text: str | None = None
    created_at: datetime
