"""Follow-graph schemas (PRD Part D, Phase 2).

The paginated user shapes are shared with people search, so they live in
``app.schemas.user``. They are re-exported here to keep the follow module's
public surface stable for existing callers.
"""

from app.schemas.user import UserPage, UserSummary

__all__ = ["UserPage", "UserSummary"]
