"""HTTP middleware.

`SecurityHeadersMiddleware` attaches the standard hardening headers to every
response (SEC-10, SEC-25, and HSTS for SEC-08). The app's user-facing HTML is
served by the frontend (Nginx), so the Content-Security-Policy that protects
the SPA lives in `frontend/nginx.conf`; these headers cover the API surface.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Applied to every response. `setdefault` semantics mean a route may still
# override a header (e.g. Cache-Control: no-store on sensitive responses).
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach hardening headers to every HTTP response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response
