"""Auth dependencies: get_current_user, require_admin.

Identity always comes from the JWT (Authorization: Bearer <token>), never
from a client-supplied user_id. Deactivated users are rejected even when
their token is still cryptographically valid (PRD B1).
"""

import jwt
from fastapi import (  # noqa: F401  (Depends is idiomatic in FastAPI defaults)
    Depends,
    HTTPException,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=True)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> models.User:
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from err
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )
    return user


_bearer_optional = HTTPBearer(auto_error=False)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_optional),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> models.User | None:
    """Return the authenticated user or None when no/invalid token is supplied.

    Used by public endpoints that still personalise the response when the
    caller happens to be logged in (e.g. ``is_following`` on a profile).
    """
    if credentials is None:
        return None
    try:
        user_id = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        return None
    user = db.get(models.User, user_id)
    if user is None or not user.is_active:
        return None
    return user


def require_admin(  # noqa: B008
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user
