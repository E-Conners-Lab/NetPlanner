"""NetPlanner FastAPI application — app factory, CORS, lifespan, routers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.middleware import SecurityHeadersMiddleware
from app.routes import advisor, comparison, projects, reports, tco

settings = get_settings()

# All API routes live under this prefix; the frontend and Nginx proxy `/api`.
API_PREFIX = "/api"

# Swagger / ReDoc / the raw schema are exposed only outside production —
# a public API does not advertise its full surface (SEC posture).
_DEV_DOCS = settings.environment != "production"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the database on startup.

    DB init fails loud — a missing/broken database is a mandatory-dependency
    failure and must not be swallowed.
    """
    await init_db()
    yield


app = FastAPI(
    title="NetPlanner API",
    version="0.1.0",
    description="AI-powered business decision support for network engineers.",
    lifespan=lifespan,
    docs_url="/docs" if _DEV_DOCS else None,
    redoc_url="/redoc" if _DEV_DOCS else None,
    openapi_url="/openapi.json" if _DEV_DOCS else None,
)

# Hardening headers on every response (SEC-08/10/25).
app.add_middleware(SecurityHeadersMiddleware)

# CORS — origins are environment-configurable (CORS_ORIGINS); dev default is
# the Vite dev server. Restricting origins is part of the transport posture.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register feature routers. advisor/tco/comparison share the `/projects`
# prefix — FastAPI merges them cleanly under one path tree.
for _router in (
    projects.router,
    advisor.router,
    tco.router,
    comparison.router,
    reports.router,
):
    app.include_router(_router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness probe — confirms the app is up and reports the environment."""
    return {"status": "ok", "environment": settings.environment}
