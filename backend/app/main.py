"""FastAPI application factory. Routers hold no business logic (PRD Part E)."""

import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.routers import all_routers

logger = logging.getLogger("chirp")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Chirp API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError):
        # Unique/constraint violations -> 409, never leak SQL.
        logger.warning("IntegrityError on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=409, content={"detail": "Resource already exists."})

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        # Never expose tracebacks/SQL/paths to clients (PRD Part L).
        logger.exception("Unhandled error on %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    for router in all_routers:
        app.include_router(router, prefix="/api/v1")

    # Phase 0 deliverable: plain GET /health (no /api/v1 prefix).
    @app.get("/health", tags=["health"], summary="Liveness check")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
