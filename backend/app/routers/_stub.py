"""Shared stub helper. Each module router returns 501 until its phase lands."""

from fastapi import APIRouter


def stub_router(prefix: str, tag: str) -> APIRouter:
    router = APIRouter(prefix=prefix, tags=[tag])

    @router.get("", status_code=501, summary=f"{tag} — not implemented yet (Phase 0 stub)")
    def _stub() -> dict:
        return {"detail": "Not implemented yet (Phase 0 stub)."}

    return router
