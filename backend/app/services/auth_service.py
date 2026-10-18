"""Team A — Authentication business logic (Phase 1).

Routers stay thin; all rules live here (PRD Part E):
lowercase normalization, duplicate handling, generic login errors,
password verification, deactivation.
"""

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.schemas.auth import RegisterRequest
from app.security import create_access_token, get_password_hash, verify_password

GENERIC_LOGIN_ERROR = "Incorrect email/username or password."


def _get_by_email(db: Session, email: str) -> models.User | None:
    return db.scalar(select(models.User).where(func.lower(models.User.email) == email))


def _get_by_username(db: Session, username: str) -> models.User | None:
    return db.scalar(select(models.User).where(func.lower(models.User.username) == username))


def register_user(db: Session, data: RegisterRequest) -> models.User:
    email = data.email.strip().lower()
    username = data.username.strip().lower()
    display_name = data.display_name.strip()

    if _get_by_email(db, email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered."
        )
    if _get_by_username(db, username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")

    user = models.User(
        email=email,
        username=username,
        password_hash=get_password_hash(data.password),
        display_name=display_name,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already taken.",
        ) from err
    db.refresh(user)
    return user


def authenticate_user(db: Session, identifier: str, password: str) -> str:
    """Validate credentials and return a signed JWT. Never reveal which part failed."""
    cleaned = identifier.strip()
    if "@" in cleaned:
        user = _get_by_email(db, cleaned.lower())
    else:
        user = _get_by_username(db, cleaned.lower())

    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_LOGIN_ERROR)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated.")
    return create_access_token(user.id)


def change_password(
    db: Session, user: models.User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect."
        )
    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )
    user.password_hash = get_password_hash(new_password)
    db.add(user)
    db.commit()


def deactivate_user(db: Session, user: models.User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password.")
    user.is_active = False
    db.add(user)
    db.commit()
