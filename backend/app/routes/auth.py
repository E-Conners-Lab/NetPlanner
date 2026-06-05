"""Authentication routes (register / login / logout / me).

The session token is delivered exclusively as an httpOnly, Secure,
``SameSite=Strict`` cookie (SEC-01 — Backend-for-Frontend). Login regenerates
the session identifier (SEC-04) by always issuing a new JWT and overwriting
the cookie, and logout bumps the user's `session_version` so prior tokens
stop validating server-side (SEC-16).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.rate_limit import limiter, rate_limit
from app.schemas.auth import LoginRequest, RegisterRequest, UserRead
from app.services import auth_service

# Dedicated security audit channel (SEC-28). Kept separate from the app log so
# operators can route it to immutable, write-only storage.
audit_logger = logging.getLogger("app.audit")

_GENERIC_LOGIN_ERROR = "Invalid email or password"

router = APIRouter(prefix="/auth", tags=["auth"])


def _audit(request: Request, event: str, **fields: Any) -> None:
    """Emit a structured security audit event (SEC-28).

    Never includes passwords, tokens, or raw PII (SEC-18) — failed logins are
    keyed by a truncated hash of the attempted email so repeated attempts on
    one account correlate without persisting the address itself.
    """
    client_ip = request.client.host if request.client else None
    audit_logger.info(
        event,
        extra={
            "event": event,
            "request_id": getattr(request.state, "request_id", None),
            "client_ip": client_ip,
            **fields,
        },
    )


def _email_fingerprint(email: str) -> str:
    """Stable, non-reversible tag for an attempted email (SEC-18)."""
    normalized = email.strip().lower().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()[:16]


def _set_session_cookie(response: Response, token: str) -> None:
    """Write the session JWT into the session cookie (SEC-01)."""
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    """Drop the session cookie from the browser."""
    settings = get_settings()
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="strict",
    )


@router.get("/csrf", status_code=status.HTTP_204_NO_CONTENT)
async def csrf() -> Response:
    """Seed the CSRF cookie (SEC-07).

    The CSRF middleware sets the ``netplanner_csrf`` cookie on any response
    that arrives without one, so this no-op GET gives the SPA a reliable way
    to obtain a token before its first mutating request.
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(rate_limit("auth_register"))
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Create a new user and start a session.

    SEC-04: a fresh session token is issued so the registration flow does not
    leave the caller unauthenticated. SEC-18: the registration log line never
    includes the password, and on a duplicate email we return 409 with a
    generic message — no information about the existing account is disclosed.
    """
    existing = await auth_service.get_user_by_email(db, payload.email)
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await auth_service.create_user(
        db, email=payload.email, password=payload.password
    )
    token = auth_service.issue_session_token(user)
    _set_session_cookie(response, token)
    _audit(request, "auth.register", user_id=user.id)
    return user


@router.post("/login", response_model=UserRead)
@limiter.limit(rate_limit("auth_login"))
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate a user and issue a session cookie.

    Returns the same generic 401 message whether the email is unknown, the
    password is wrong, or the account is locked (SEC-06 / SEC-18 — no
    user-enumeration through error differentiation). Five consecutive failures
    lock the account for 15 minutes; every attempt is written to the audit log.
    """
    user = await auth_service.get_user_by_email(db, payload.email)

    if user is not None and auth_service.is_account_locked(user):
        _audit(request, "auth.login.locked", user_id=user.id)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_LOGIN_ERROR)

    if user is None or not auth_service.verify_password(
        user.password_hash, payload.password
    ):
        if user is not None:
            await auth_service.register_failed_login(db, user)
        _audit(
            request,
            "auth.login.failure",
            email_fp=_email_fingerprint(payload.email),
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_LOGIN_ERROR)

    await auth_service.register_successful_login(db, user)
    token = auth_service.issue_session_token(user)
    _set_session_cookie(response, token)
    _audit(request, "auth.login.success", user_id=user.id)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Invalidate the user's existing tokens and clear the cookie (SEC-16)."""
    await auth_service.bump_session_version(db, user)
    _clear_session_cookie(response)
    _audit(request, "auth.logout", user_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
async def me(request: Request, user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user (used by the SPA on boot)."""
    return user
