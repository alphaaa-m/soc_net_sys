"""Application settings loaded from environment / .env (pydantic-settings).

All secrets and environment-specific values live here. Code must read them
via ``get_settings()`` — never hardcode secrets or import ``os.environ``
directly in routers/services.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    DATABASE_URL: str = (
        "postgresql+psycopg2://postgres:change_me@localhost:5432/CHIRP"
    )
    SECRET_KEY: str = "replace-with-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:3000"

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _keep_raw(cls, v: str) -> str:
        return v

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
