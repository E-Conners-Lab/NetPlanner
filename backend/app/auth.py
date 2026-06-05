"""Auth dependencies — `get_current_user` resolves the session JWT cookie.

The session JWT is delivered exclusively via an httpOnly, Secure-by-default,
``SameSite=Strict`` cookie (SEC-01 — Backend-for-Frontend pattern). The token
is **never** read from an ``Authorization`` header: a JWT-in-header path would
invite a future client to hold the token in JS-readable memory, reintroducing
the XSS-exfiltration vector SEC-01 exists to close. The SSE client authenticates
with the same cookie (``fetch(..., {credentials: 'include'})``).
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.services import auth_service

_UNAUTHORIZED = "Authentication required"


def _extract_token(request: Request) -> str | None:
    """Pull the session token from the httpOnly session cookie (SEC-01)."""
    settings = get_settings()
    return request.cookies.get(settings.session_cookie_name) or None


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the authenticated user or raise 401 (SEC-02).

    The cookie/JWT version must match the user's current `session_version`;
    a logout bumps that counter so prior tokens stop validating (SEC-16).
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)

    try:
        payload = auth_service.decode_session_token(token)
    except jwt.InvalidTokenError as exc:
        # Generic error to the caller; the structured logger keeps the detail.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED) from exc

    user_id = payload.get("sub")
    token_version = payload.get("ver")
    if not isinstance(user_id, str) or not isinstance(token_version, int):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None or user.session_version != token_version:
        # Token references a deleted user or one whose sessions were rotated.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_UNAUTHORIZED)

    return user
