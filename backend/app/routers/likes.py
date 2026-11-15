"""Team A — Like endpoints (Phase 3, PRD B7 + Part D).

Thin HTTP layer over ``services/like_service.py``. The routes are mounted on
``/posts`` because a like acts on a post; the module keeps its own file per the
PM Plan ownership map.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.schemas.like import LikeRead
from app.services import like_service

router = APIRouter(tags=["likes"])


@router.post(
    "/posts/{post_id}/like",
    response_model=LikeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Like a post",
    description=(
        "Creates a like for the current user. Liking twice is 409 and a "
        "missing or soft-deleted post is 404."
    ),
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Post not found or deleted"},
        409: {"description": "Post already liked"},
    },
)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> models.PostLike:
    return like_service.like_post(db, current, post_id)


@router.delete(
    "/posts/{post_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlike a post",
    description=(
        "Removes the current user's like. Returns 404 when the post is gone "
        "or when it was not liked."
    ),
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "Post not found or not liked"},
    },
)
def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> None:
    like_service.unlike_post(db, current, post_id)
    return None
