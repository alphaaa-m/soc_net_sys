"""User profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.schemas.users import ProfileUpdate, UserMe, UserPublic
from app.services.user_service import get_public_user, update_profile

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserMe,
    summary="Get my profile",
    description="Returns the authenticated user's private profile, including their email.",
)
def read_my_profile(
    current_user: models.User = Depends(get_current_user),  # noqa: B008
) -> models.User:
    return current_user


@router.patch(
    "/me",
    response_model=UserMe,
    summary="Update my profile",
    description="Updates the authenticated user's display name and/or bio.",
)
def patch_my_profile(
    profile: ProfileUpdate,
    current_user: models.User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> models.User:
    return update_profile(db, current_user, profile.model_dump(exclude_unset=True))


@router.get(
    "/{username}",
    response_model=UserPublic,
    summary="Get a public profile",
    responses={404: {"description": "User not found."}},
)
def read_public_profile(
    username: str,
    db: Session = Depends(get_db),  # noqa: B008
) -> models.User:
    user = get_public_user(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user
