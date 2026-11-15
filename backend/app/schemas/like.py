"""Post-like schemas (PRD B7, Phase 3 — Team A).

Likes are a pure relationship row: ``(user_id, post_id)`` is the composite
primary key, so the response mirrors that pair. Counts are served by the post
response (wiring PR) and the bulk helpers in ``like_service``.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LikeRead(BaseModel):
    """The like relationship created by ``POST /posts/{post_id}/like``."""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    post_id: int
    created_at: datetime
