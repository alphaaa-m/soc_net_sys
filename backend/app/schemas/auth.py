<<<<<<< HEAD
"""Team A — Authentication schemas (Phase 1).

Request/response shapes for /auth/* (PRD Parts B1 + D). Response models
never include ``password`` or ``password_hash``.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("username")
    @classmethod
    def _normalize_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not (3 <= len(v) <= 30):
            raise ValueError("Username must be 3-30 characters.")
        if not USERNAME_RE.match(v):
            raise ValueError("Username may only contain letters, numbers and underscore.")
        return v

    @field_validator("display_name")
    @classmethod
    def _strip_display_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Display name must not be empty.")
        return v


class UserRegistered(BaseModel):
    """201 response for POST /auth/register (public fields + email)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    display_name: str
    bio: str | None = None
    role: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("identifier")
    @classmethod
    def _strip_identifier(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Identifier must not be empty.")
        return v


class TokenResponse(BaseModel):
=======
"""Authentication request/response schemas (PRD B1, Part D).

These models only describe and validate the shape of API data. Business rules
(duplicate checks, password comparison, token issuing) live in
``app.services.auth_service``.
"""

import re

from pydantic import BaseModel, Field, field_validator

# Deliberately dependency-free email check (avoids adding `email-validator`).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_USERNAME_PATTERN = r"^[A-Za-z0-9_]+$"

# bcrypt hashes at most 72 bytes; reject longer input here so it becomes a
# clean 422 instead of a 500 raised deep inside the hashing library.
_BCRYPT_MAX_BYTES = 72


class RegisterIn(BaseModel):
    """Body for ``POST /auth/register``."""

    email: str = Field(min_length=3, max_length=255)
    username: str = Field(min_length=3, max_length=30, pattern=_USERNAME_PATTERN)
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=1, max_length=50)

    @field_validator("email", mode="before")
    @classmethod
    def _clean_email(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip().lower()
            if not _EMAIL_RE.match(value):
                raise ValueError("Invalid email address.")
        return value

    @field_validator("username", mode="before")
    @classmethod
    def _clean_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("display_name", mode="before")
    @classmethod
    def _clean_display_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("password")
    @classmethod
    def _password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > _BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be at most {_BCRYPT_MAX_BYTES} bytes.")
        return value


class LoginIn(BaseModel):
    """Body for ``POST /auth/login``. ``identifier`` is an email or a username."""

    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1)


class TokenOut(BaseModel):
    """Response for a successful login."""

>>>>>>> master
    access_token: str
    token_type: str = "bearer"


<<<<<<< HEAD
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DeactivateRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
=======
class PasswordChangeIn(BaseModel):
    """Body for ``PUT /auth/password``."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def _password_within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > _BCRYPT_MAX_BYTES:
            raise ValueError(f"Password must be at most {_BCRYPT_MAX_BYTES} bytes.")
        return value


class DeactivateIn(BaseModel):
    """Body for ``POST /auth/deactivate``."""

    password: str = Field(min_length=1)
>>>>>>> master
