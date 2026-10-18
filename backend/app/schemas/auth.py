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
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DeactivateRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
