"""User/profile HTTP layer (PRD B2). Routers stay thin — rules live in user_service."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.schemas import user as user_schemas
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=user_schemas.UserMe,
    summary="Get my own account (includes email)",
)
def read_me(
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> models.User:
    return current


@router.patch(
    "/me",
    response_model=user_schemas.UserMe,
    summary="Update my display name / bio",
)
def update_me(
    payload: user_schemas.UserUpdate,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> models.User:
    return user_service.update_profile(db, current, payload.model_dump(exclude_unset=True))


@router.get(
    "/{username}",
    response_model=user_schemas.UserProfile,
    summary="View a public profile by username",
)
def read_profile(
    username: str,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User | None = Depends(get_current_user_optional),  # noqa: B008
) -> user_schemas.UserProfile:
    return user_service.get_profile(db, username, current)
