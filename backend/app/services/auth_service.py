<<<<<<< HEAD
"""Team A — Authentication business logic (Phase 1).

Routers stay thin; all rules live here (PRD Part E):
lowercase normalization, duplicate handling, generic login errors,
password verification, deactivation.
"""

from fastapi import HTTPException, status
from sqlalchemy import func, select
=======
"""Authentication business rules (PRD B1).

Routers delegate here; this module owns the rules: normalising input,
preventing duplicates, verifying passwords and deactivation semantics.
"""

from datetime import UTC, datetime

from sqlalchemy import or_
>>>>>>> master
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
<<<<<<< HEAD
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
=======
from app.exceptions import bad_request, conflict, forbidden, unauthorized
from app.security import get_password_hash, verify_password


def _normalise(identifier: str) -> str:
    """Usernames and emails are stored lowercase (PRD B1)."""
    return identifier.strip().lower()


def register_user(
    db: Session,
    *,
    email: str,
    username: str,
    password: str,
    display_name: str,
) -> models.User:
    """Create a new account with a hashed password; 409 on duplicates."""
    email = _normalise(email)
    username = _normalise(username)

    if db.query(models.User).filter(models.User.email == email).first() is not None:
        raise conflict("Email is already registered.")
    if db.query(models.User).filter(models.User.username == username).first() is not None:
        raise conflict("Username is already taken.")
>>>>>>> master

    user = models.User(
        email=email,
        username=username,
<<<<<<< HEAD
        password_hash=get_password_hash(data.password),
        display_name=display_name,
=======
        password_hash=get_password_hash(password),
        display_name=display_name,
        role="user",
        is_active=True,
>>>>>>> master
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as err:
<<<<<<< HEAD
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already taken.",
        ) from err
=======
        # Two requests raced past the checks above; the unique constraints are
        # the real guard (PRD B1).
        db.rollback()
        raise conflict("Email or username is already registered.") from err
>>>>>>> master
    db.refresh(user)
    return user


<<<<<<< HEAD
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
=======
def authenticate(db: Session, identifier: str, password: str) -> models.User:
    """Return the matching active user or raise 401/403.

    The same generic message is used for "no such user" and "wrong password"
    so callers cannot probe which accounts exist (PRD B1).
    """
    ident = _normalise(identifier)
    user = (
        db.query(models.User)
        .filter(or_(models.User.email == ident, models.User.username == ident))
        .first()
    )
    if user is None or not verify_password(password, user.password_hash):
        raise unauthorized("Could not validate credentials")
    if not user.is_active:
        raise forbidden("Account is deactivated.")
    return user


def change_password(
    db: Session,
    user: models.User,
    *,
    current_password: str,
    new_password: str,
) -> None:
    """Change the password after verifying the current one (PRD B1)."""
    if not verify_password(current_password, user.password_hash):
        raise unauthorized("Current password is incorrect.")
    if verify_password(new_password, user.password_hash):
        raise bad_request("New password must be different from the current password.")
    user.password_hash = get_password_hash(new_password)
    user.updated_at = datetime.now(UTC)
    db.commit()


def deactivate_account(db: Session, user: models.User, *, password: str) -> None:
    """Soft-disable the account. Requires the password (PRD B1)."""
    if not verify_password(password, user.password_hash):
        raise unauthorized("Password is incorrect.")
    user.is_active = False
    user.updated_at = datetime.now(UTC)
>>>>>>> master
    db.commit()
