"""NetPlanner FastAPI application — app factory, CORS, lifespan, routers."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import get_settings
from app.csrf import CSRFMiddleware
from app.database import AsyncSessionLocal, init_db
from app.middleware import RequestIDMiddleware, SecurityHeadersMiddleware
from app.rate_limit import limiter, rate_limit_handler
from app.routes import advisor, auth, comparison, projects, reports, tco

logger = logging.getLogger(__name__)

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

# Wire up the rate limiter (SEC-06) before mounting routes so its decorators
# resolve correctly.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]

# Hardening headers on every response (SEC-08/10/25).
app.add_middleware(SecurityHeadersMiddleware)
# CSRF double-submit enforcement on mutating /api requests (SEC-07).
app.add_middleware(CSRFMiddleware)
# Correlation ID on every request — surfaces a stable id in logs and the
# response header so an operator can chase a single user-visible error back
# through structured log lines.
app.add_middleware(RequestIDMiddleware)

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
    auth.router,
    projects.router,
    advisor.router,
    tco.router,
    comparison.router,
    reports.router,
):
    app.include_router(_router, prefix=API_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness probe — confirms the process is up. No DB hit (intentional)."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/ready", tags=["health"])
async def ready(response: Response) -> dict:
    """Readiness probe — confirms the DB is reachable and at head.

    Used by orchestrators to gate traffic. Returns HTTP 503 when the database
    is unreachable so load balancers actually stop routing to the instance —
    a 200 with a "not_ready" body would be silently kept in rotation.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — health probe surfaces all errors
        logger.warning("readiness check failed: %s", exc)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "error": "database unavailable"}
    return {"status": "ready", "environment": settings.environment}
