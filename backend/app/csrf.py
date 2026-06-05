"""CSRF protection — double-submit cookie pattern (SEC-07).

``SameSite=Strict`` on the session cookie is the first line of defense, but the
Secure Build Standard treats SameSite as insufficient on its own (Safari/Firefox
have no Lax default; Chromium's Lax-default has a 120-second post-navigation
window). So every state-changing request must also carry a CSRF token.

Mechanism: a random token is issued in the non-httpOnly ``netplanner_csrf``
cookie. The SPA reads that cookie and echoes it in the ``X-CSRF-Token`` header
on every mutating request. The server compares the two with a constant-time
comparison (SEC-26). A cross-site attacker can neither read the victim's cookie
(it is same-origin only) nor set the custom header cross-site, so the request
fails closed.

Safe methods (GET/HEAD/OPTIONS) are never enforced and seed the cookie when it
is missing, so the SPA always has a token before its first mutating call. The
limiter-style env flag ``NETPLANNER_CSRF_ENABLED=0`` disables enforcement for
the test suite (opted back in by ``test_csrf``).
"""

from __future__ import annotations

import hmac
import os
import secrets
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import Settings, get_settings

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
_API_PREFIX = "/api"


def issue_csrf_token() -> str:
    """Return a fresh, URL-safe CSRF token."""
    return secrets.token_urlsafe(32)


def _enabled() -> bool:
    """CSRF enforcement is on unless a test fixture flips it off."""
    return os.environ.get("NETPLANNER_CSRF_ENABLED", "1") != "0"


def _set_csrf_cookie(response: Response, settings: Settings) -> None:
    """Seed a new CSRF cookie (readable by the SPA, not httpOnly)."""
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=issue_csrf_token(),
        max_age=settings.session_max_age_seconds,
        httponly=False,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )


class CSRFMiddleware(BaseHTTPMiddleware):
    """Enforce the double-submit CSRF token on mutating ``/api`` requests."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        existing = request.cookies.get(settings.csrf_cookie_name)

        if (
            _enabled()
            and request.method not in _SAFE_METHODS
            and request.url.path.startswith(_API_PREFIX)
        ):
            header = request.headers.get(settings.csrf_header_name, "")
            if not existing or not header or not hmac.compare_digest(existing, header):
                # Generic message (SEC-11). Seed a token so the client can retry.
                rejected = JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed."},
                )
                if not existing:
                    _set_csrf_cookie(rejected, settings)
                return rejected

        response = await call_next(request)
        if not existing:
            _set_csrf_cookie(response, settings)
        return response
