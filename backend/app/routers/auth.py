"""Team A — Authentication router (Phase 1).

Thin HTTP layer over services/auth_service.py (PRD Parts B1 + D).
Logout is stateless: the server holds no sessions, so the client
simply discards its JWT; this endpoint exists for API completeness.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.deps import get_current_user
from app.schemas.auth import (
    ChangePasswordRequest,
    DeactivateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserRegistered,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRegistered,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    description="Creates a user with a hashed password. Email/username are stored lowercase.",
    responses={
        409: {"description": "Duplicate email or username"},
        422: {"description": "Invalid body"},
    },
)
def register(data: RegisterRequest, db: Session = Depends(get_db)) -> models.User:
    return auth_service.register_user(db, data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in with email or username",
    description="Accepts an email address or username plus password; returns a JWT access token.",
    responses={
        401: {"description": "Bad credentials"},
        403: {"description": "Deactivated account"},
    },
)
def login(data: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    token = auth_service.authenticate_user(db, data.identifier, data.password)
    return TokenResponse(access_token=token, token_type="bearer")


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out (client discards token)",
    description=(
        "Stateless JWT logout: the server keeps no session or denylist, "
        "so logout means the client deletes its token. Requires a valid token."
    ),
    responses={401: {"description": "Missing/invalid token"}},
)
def logout(current_user: models.User = Depends(get_current_user)) -> None:
    _ = current_user
    return None


@router.put(
    "/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change password",
    description="Verifies the current password, then stores a hash of the new password.",
    responses={
        400: {"description": "Wrong current password or new password identical"},
        401: {"description": "Missing/invalid token"},
        422: {"description": "Invalid body"},
    },
)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    auth_service.change_password(db, current_user, data.current_password, data.new_password)
    return None


@router.post(
    "/deactivate",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate own account",
    description=(
        "Re-verifies the password, then sets is_active=false. "
        "Deactivated users cannot log in."
    ),
    responses={401: {"description": "Missing/invalid token or wrong password"}},
)
def deactivate(
    data: DeactivateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    auth_service.deactivate_user(db, current_user, data.password)
    return None
