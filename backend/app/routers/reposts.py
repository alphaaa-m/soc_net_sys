"""Team A — Repost endpoints (Phase 3, PRD B8 + Part D).

Thin HTTP layer over ``services/repost_service.py``. The body is optional:
``POST /posts/{post_id}/repost`` works with no body, an empty object, or
``{"quote_text": "..."}``.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.schemas.repost import RepostCreate, RepostRead
from app.services import repost_service

router = APIRouter(tags=["reposts"])


@router.post(
    "/posts/{post_id}/repost",
    response_model=RepostRead,
    status_code=status.HTTP_201_CREATED,
    summary="Repost a post (optional quote)",
    description=(
        "Reposts someone else's post. Self-repost is 403, a duplicate is 409 "
        "and a missing or soft-deleted post is 404. Quote text is optional and "
        "limited to 280 characters."
    ),
    responses={
        401: {"description": "Missing/invalid token"},
        403: {"description": "Cannot repost your own post"},
        404: {"description": "Post not found or deleted"},
        409: {"description": "Post already reposted"},
        422: {"description": "Invalid quote text"},
    },
)
def repost_post(
    post_id: int,
    payload: RepostCreate | None = None,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> models.Repost:
    quote_text = payload.quote_text if payload is not None else None
    return repost_service.repost_post(db, current, post_id, quote_text)


@router.delete(
    "/posts/{post_id}/repost",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Undo a repost",
    description=("Removes the current user's repost. Returns 404 when the repost does not exist."),
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Repost not found"},
    },
)
def unrepost_post(
    post_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> None:
    repost_service.unrepost_post(db, current, post_id)
    return None
