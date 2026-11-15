"""Team A — Follow system router (Phase 2).

Thin HTTP layer over services/follow_service.py (PRD Parts B3 + D).
The routes live under ``/users`` because they act on a user; the file
itself is Team A's module router (PM Plan ownership map).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.pagination import pagination
from app.schemas.follow import FollowList, FollowRead
from app.services import follow_service

router = APIRouter(prefix="/users", tags=["follows"])


@router.put(
    "/{user_id}/follow",
    response_model=FollowRead,
    status_code=status.HTTP_201_CREATED,
    summary="Follow a user",
    description=(
        "Creates the follow relationship. Self-follow is 400, missing or "
        "deactivated targets are 404, and an existing follow is 409."
    ),
    responses={
        400: {"description": "Cannot follow yourself"},
        401: {"description": "Missing/invalid token"},
        404: {"description": "Target user not found or deactivated"},
        409: {"description": "Already following this user"},
    },
)
def follow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Follow:
    return follow_service.follow_user(db, current_user, user_id)


@router.delete(
    "/{user_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unfollow a user",
    description=(
        "Removes the follow relationship. Returns 404 when the relationship "
        "(or the target user) does not exist."
    ),
    responses={
        401: {"description": "Missing/invalid token"},
        404: {"description": "User not found or not currently followed"},
    },
)
def unfollow_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    follow_service.unfollow_user(db, current_user, user_id)
    return None


@router.get(
    "/{username}/followers",
    response_model=FollowList,
    summary="List a user's followers",
    description=(
        "Public, paginated list of active users following ``username``. "
        "Deactivated accounts are hidden. limit max is 50."
    ),
    responses={
        404: {"description": "User not found or deactivated"},
        422: {"description": "Invalid pagination"},
    },
)
def list_followers(
    username: str,
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
) -> FollowList:
    items, total = follow_service.list_followers(db, username, page["limit"], page["offset"])
    return FollowList(items=items, total=total, **page)


@router.get(
    "/{username}/following",
    response_model=FollowList,
    summary="List users a user is following",
    description=(
        "Public, paginated list of active users followed by ``username``. "
        "Deactivated accounts are hidden. limit max is 50."
    ),
    responses={
        404: {"description": "User not found or deactivated"},
        422: {"description": "Invalid pagination"},
    },
)
def list_following(
    username: str,
    page: dict = Depends(pagination),
    db: Session = Depends(get_db),
) -> FollowList:
    items, total = follow_service.list_following(db, username, page["limit"], page["offset"])
    return FollowList(items=items, total=total, **page)
