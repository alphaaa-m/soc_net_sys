"""Request and response schemas for user profiles."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UserPublic(BaseModel):
    """Fields safe to expose on a public profile."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    bio: str | None
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0


class UserMe(UserPublic):
    """Private profile returned only to the authenticated account owner."""

    email: str


class ProfileUpdate(BaseModel):
    """Fields a user may update on their own profile."""

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    bio: str | None = Field(default=None, max_length=160)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        return value.strip() if value is not None else None

    @model_validator(mode="after")
    def validate_update(self) -> "ProfileUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one profile field must be provided.")
        if "display_name" in self.model_fields_set and self.display_name is None:
            raise ValueError("display_name cannot be null.")
        if self.display_name == "":
            raise ValueError("display_name must contain at least one non-whitespace character.")
        return self
