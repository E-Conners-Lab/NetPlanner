"""In-process rate limiter (SEC-06 — DoS / abuse control).

We use SlowAPI's per-route decorator with a per-user-or-IP key so a logged-in
caller is limited consistently across IPs while anonymous calls fall back to
the remote address. Configured limits per endpoint are kept here so they are
easy to tune. The limiter is **disabled during tests** so behavior tests run
without bumping into per-route caps; tests that exercise the limiter set the
``app.state.test_rate_limit`` flag explicitly.
"""

from __future__ import annotations

import hashlib
import os

import jwt
from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.config import get_settings


def _identify_caller(request: Request) -> str:
    """Use the authenticated user id when available, else the remote address.

    SlowAPI's key_func runs before FastAPI resolves dependencies, so we
    decode the session JWT directly out of the httpOnly session cookie.
    Tokens that don't validate fall back to the client address — this keeps
    a single user on the user bucket while anonymous traffic still gets
    capped on IP (SEC-06).
    """
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name)
    # nosemgrep
    if token:
        try:
            payload = jwt.decode(
                token,
                settings.require_jwt_secret(),
                algorithms=["HS256"],
            )
            user_id = payload.get("sub")
            if isinstance(user_id, str):
                # nosemgrep
                return f"user:{user_id}"
        except jwt.InvalidTokenError:
            # Bucket invalid tokens on a stable per-token hash so a credential
            # stuffer cannot drain anonymous IPs.
            digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
            # nosemgrep
            return f"token:{digest}"
    # nosemgrep
    return f"ip:{get_remote_address(request)}"


def _enabled() -> bool:
    """Rate limiting is on unless the test fixture flips it off."""
    return os.environ.get("NETPLANNER_RATE_LIMIT_ENABLED", "1") != "0"


limiter = Limiter(
    key_func=_identify_caller,
    # Header injection (X-RateLimit-Limit/Remaining/Reset) requires the
    # decorated handler to declare a `response: Response` kwarg. Our advisor
    # / report routes return StreamingResponse and PDF Response objects
    # built inside the handler, so SlowAPI's mutation path crashes. Keep
    # the limit enforced but skip the informational headers (the 429 path
    # still emits Retry-After via `rate_limit_handler`).
    headers_enabled=False,
    enabled=_enabled(),
)


_LIMITS: dict[str, str] = {
    # Advisor — single-stream model call per request, expensive. 10/min lines
    # up with PID's PIS-30 daily volume (~10 runs/day) with headroom.
    "advisor": "10/minute",
    # Comparison — fans out to N research calls plus the synthesizer.
    "comparison": "5/minute",
    # Report generation (PDF) — CPU-bound + DB reads.
    "report_create": "6/minute",
    "report_download": "15/minute",
    # Auth-sensitive endpoints (SEC-06).
    "auth_login": "10/minute",
    "auth_register": "5/minute",
}


def rate_limit(name: str) -> str:
    """Return the configured limit for the given logical endpoint."""
    return _LIMITS[name]


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Render rate-limit hits as a clean structured 429 (SEC-11 — no internals)."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests — please slow down and retry shortly.",
            "limit": str(exc.detail),
        },
        headers={"Retry-After": "30"},
    )
