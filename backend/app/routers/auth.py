"""Auth HTTP layer (PRD B1). Routers stay thin — rules live in auth_service."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.schemas import auth as auth_schemas
from app.schemas import user as user_schemas
from app.security import create_access_token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=user_schemas.UserMe,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def register(
    payload: auth_schemas.RegisterIn,
    db: Session = Depends(get_db),  # noqa: B008
) -> models.User:
    return auth_service.register_user(
        db,
        email=payload.email,
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
    )


@router.post(
    "/login",
    response_model=auth_schemas.TokenOut,
    summary="Log in and receive a JWT",
)
def login(
    payload: auth_schemas.LoginIn,
    db: Session = Depends(get_db),  # noqa: B008
) -> auth_schemas.TokenOut:
    user = auth_service.authenticate(db, payload.identifier, payload.password)
    return auth_schemas.TokenOut(access_token=create_access_token(user.id))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (client discards the token)",
)
def logout(
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> None:
    # Stateless JWTs: there is nothing server-side to invalidate; the client
    # simply drops the token (PRD B1).
    return None


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current password",
)
def change_password(
    payload: auth_schemas.PasswordChangeIn,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> None:
    auth_service.change_password(
        db,
        current,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return None


@router.post(
    "/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate the current account",
)
def deactivate(
    payload: auth_schemas.DeactivateIn,
    db: Session = Depends(get_db),  # noqa: B008
    current: models.User = Depends(get_current_user),  # noqa: B008
) -> None:
    auth_service.deactivate_account(db, current, password=payload.password)
    return None
