"""Liveness check (Phase 0 deliverable)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
def health() -> dict:
    return {"status": "ok"}
