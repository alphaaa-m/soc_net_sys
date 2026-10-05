"""Shared dependencies: pagination params used by every list endpoint."""

from fastapi import Query

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def pagination(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> dict:
    return {"limit": limit, "offset": offset}
