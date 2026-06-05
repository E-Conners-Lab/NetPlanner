"""HTTP middleware.

`SecurityHeadersMiddleware` attaches the standard hardening headers to every
response (SEC-10, SEC-25, and HSTS for SEC-08 when explicitly enabled).
`RequestIDMiddleware` echoes / generates a stable `X-Request-ID` per request
so logs can be correlated end-to-end.

The app's user-facing HTML is served by the frontend (Nginx), so the
Content-Security-Policy that protects the SPA lives in `frontend/nginx.conf`;
these headers cover the API surface.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import get_settings

logger = logging.getLogger("app.access")

# Headers applied unconditionally. The API only ever returns JSON or PDF —
# never HTML that loads scripts — so a deny-all CSP is safe and closes the
# framing / script-injection surface on the API origin itself (SEC-09/10/25).
_BASE_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
_HSTS_HEADER = ("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every HTTP response.

    HSTS is sent automatically in production and whenever the operator opts in
    via ``ENABLE_HSTS=1``. It stays off for non-production HTTP development,
    where ``max-age=31536000`` would pin the browser to HTTPS-only for a year
    and break local work (SEC-08). ``Cache-Control: no-store`` is set on the
    whole ``/api`` surface because every response there is session-bound or
    carries PII — browsers and intermediaries must not cache it (SEC-24).
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header, value in _BASE_SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        settings = get_settings()
        if settings.enable_hsts or settings.environment == "production":
            response.headers.setdefault(*_HSTS_HEADER)
        if request.url.path.startswith("/api"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach an ``X-Request-ID`` to every request/response and log access.

    Honors a caller-supplied ID when present (handy when a frontend wants its
    client-side correlation key to flow through), otherwise generates one.
    The structured log line emitted here is keyed by request id so an
    operator can chase a single failure back through the journal.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id

        started = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = int((time.perf_counter() - started) * 1000)
            status_code = getattr(response, "status_code", 500)
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            if response is not None:
                response.headers.setdefault("X-Request-ID", request_id)
