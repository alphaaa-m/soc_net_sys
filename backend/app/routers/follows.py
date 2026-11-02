"""Follow HTTP layer (PRD Part D, Phase 2). Rules live in follow_service."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.pagination import pagination
from app.schemas import follow as follow_schemas
from app.services import follow_service

router = APIRouter(prefix="/users", tags=["follows"])


@router.put(
    "/{user_id}/follow",
    status_code=status.HTTP_201_CREATED,
    summary="Follow a user (409 if already following)",
)
def follow(
    user_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> dict:
    follow_service.follow_user(db, current, user_id)
    return {"detail": "Now following this user."}


@router.delete(
    "/{user_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unfollow a user (404 if not following)",
)
def unfollow(
    user_id: int,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> None:
    follow_service.unfollow_user(db, current, user_id)
    return None


@router.get(
    "/{username}/followers",
    response_model=follow_schemas.UserPage,
    summary="List a user's followers",
)
def followers(
    username: str,
    page: dict = Depends(pagination),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User | None = Depends(get_current_user_optional),  # noqa: B008
) -> follow_schemas.UserPage:
    return follow_service.list_followers(
        db,
        username,
        limit=page["limit"],
        offset=page["offset"],
        current=current,
    )


@router.get(
    "/{username}/following",
    response_model=follow_schemas.UserPage,
    summary="List the users a user follows",
)
def following(
    username: str,
    page: dict = Depends(pagination),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User | None = Depends(get_current_user_optional),  # noqa: B008
) -> follow_schemas.UserPage:
    return follow_service.list_following(
        db,
        username,
        limit=page["limit"],
        offset=page["offset"],
        current=current,
    )
