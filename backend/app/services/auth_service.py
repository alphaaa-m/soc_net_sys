"""Authentication business rules (PRD B1).

Routers delegate here; this module owns the rules: normalising input,
preventing duplicates, verifying passwords and deactivation semantics.
"""

from datetime import UTC, datetime

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
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

    user = models.User(
        email=email,
        username=username,
        password_hash=get_password_hash(password),
        display_name=display_name,
        role="user",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as err:
        # Two requests raced past the checks above; the unique constraints are
        # the real guard (PRD B1).
        db.rollback()
        raise conflict("Email or username is already registered.") from err
    db.refresh(user)
    return user


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
    db.commit()
