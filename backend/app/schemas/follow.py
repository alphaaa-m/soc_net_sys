"""Follow-graph request/response schemas (PRD Part D, Phase 2)."""

from pydantic import BaseModel


class UserSummary(BaseModel):
    """A user as shown inside follower/following lists.

    Counts are intentionally omitted here: they belong on the full profile, and
    leaving them out keeps the list query free of per-row count queries.
    """

    id: int
    username: str
    display_name: str
    bio: str | None = None
    is_following: bool = False


class UserPage(BaseModel):
    """Paginated user list (PRD response standard)."""

    items: list[UserSummary]
    limit: int
    offset: int
    total: int
