"""Authentication / identity data layer (SEC-01, SEC-04, SEC-17).

Two responsibilities live here:

1. **Password hashing.** Argon2id with the OWASP 2026 baseline parameters
   (m=19 MiB, t=2, p=1) via `argon2-cffi`. The raw password never leaves this
   module — it is hashed before persistence and verified with a constant-time
   comparison provided by the library.

2. **Session JWT issuance and verification.** The token is small and signed
   (HS256). It encodes the user id, a per-user `session_version` (bumped on
   logout / password change so prior tokens stop validating — SEC-16), and a
   short expiry. The token is delivered exclusively as an httpOnly,
   Secure-by-default, SameSite=Strict cookie (SEC-01).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import User

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass

# OWASP 2026 baseline (Argon2id) parameters. `argon2-cffi` defaults already
# match this; we set them explicitly so a future library change does not
# silently weaken the hash.
_HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19 * 1024,  # 19 MiB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)

_JWT_ALG = "HS256"

# Brute-force defense (SEC-06): lock an account after this many consecutive
# failed logins, for this long. The window resets on any successful login.
_MAX_FAILED_ATTEMPTS = 5
_LOCKOUT_DURATION = timedelta(minutes=15)


def hash_password(plain: str) -> str:
    """Return an Argon2id hash of the given plaintext password (SEC-17)."""
    return _HASHER.hash(plain)


def verify_password(stored_hash: str, plain: str) -> bool:
    """Constant-time verification of a password against its stored hash.

    Returns ``False`` on any failure mode (mismatch, malformed hash). A
    legitimate library exception still bubbles up so a corrupted hash is
    surfaced rather than swallowed.
    """
    try:
        return _HASHER.verify(stored_hash, plain)
    except (VerifyMismatchError, InvalidHashError):
        return False


def issue_session_token(user: User, *, expires_in: int | None = None) -> str:
    """Create a JWT for the given user (SEC-01 / SEC-16).

    Args:
        user: The authenticated user.
        expires_in: Override the configured TTL (seconds). Tests use this to
            mint near-expiry tokens.
    """
    settings = get_settings()
    ttl = expires_in if expires_in is not None else settings.session_max_age_seconds
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user.id,
        "ver": user.session_version,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
    }
    return jwt.encode(payload, settings.require_jwt_secret(), algorithm=_JWT_ALG)


def decode_session_token(token: str) -> dict[str, Any]:
    """Decode and validate a session JWT.

    Raises:
        jwt.InvalidTokenError: token is missing, expired, tampered, or
            otherwise unacceptable.
    """
    settings = get_settings()
    return jwt.decode(token, settings.require_jwt_secret(), algorithms=[_JWT_ALG])


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    """Return a user by id, or ``None`` if not found."""
    return await db.get(User, user_id)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Return a user by email (case-insensitive), or ``None`` if not found."""
    normalized = email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, *, email: str, password: str) -> User:
    """Create a user with an Argon2id-hashed password.

    Caller is responsible for ensuring the email is not already taken — the
    route layer returns the appropriate 409. The DB unique constraint is the
    last-line safety net.
    """
    user = User(
        email=email.strip().lower(),
        password_hash=hash_password(password),
        session_version=1,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def bump_session_version(db: AsyncSession, user: User) -> None:
    """Invalidate every existing session token for the user (SEC-16)."""
    user.session_version += 1
    await db.commit()


def is_account_locked(user: User) -> bool:
    """Return ``True`` while the user is inside an active lockout window."""
    if user.locked_until is None:
        return False
    return user.locked_until > datetime.now(UTC)


async def register_failed_login(db: AsyncSession, user: User) -> None:
    """Record a failed login and lock the account once the threshold is hit.

    On reaching ``_MAX_FAILED_ATTEMPTS`` consecutive failures the account is
    locked for ``_LOCKOUT_DURATION`` and the counter resets, so a fresh window
    begins after the lock expires (SEC-06).
    """
    user.failed_login_count += 1
    if user.failed_login_count >= _MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(UTC) + _LOCKOUT_DURATION
        user.failed_login_count = 0
    await db.commit()


async def register_successful_login(db: AsyncSession, user: User) -> None:
    """Clear any failed-attempt state after a successful authentication."""
    if user.failed_login_count or user.locked_until is not None:
        user.failed_login_count = 0
        user.locked_until = None
        await db.commit()
