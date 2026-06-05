"""Shared pytest fixtures for the backend test suite.

Each test runs against an isolated in-memory SQLite database. `StaticPool`
keeps a single connection alive so the in-memory schema persists for the
duration of a test, and the FastAPI `get_db` dependency is overridden to use
the test session.

Tests are authenticated by default — most fixtures depend on `auth_user` /
`client` which create a single user and attach their JWT session cookie. The
`anon_client` fixture leaves the request unauthenticated for tests that
exercise the auth boundary directly. Rate limiting is disabled across the
suite (`NETPLANNER_RATE_LIMIT_ENABLED=0` set before any `app.*` import) and
opted back in by individual tests that need it.
"""

from __future__ import annotations

import os

# Disable rate limiting + CSRF enforcement and force a non-Secure cookie
# default before importing app modules so the middleware picks up the test
# values. CSRF is re-enabled per-test in test_csrf.py.
os.environ.setdefault("NETPLANNER_RATE_LIMIT_ENABLED", "0")
os.environ.setdefault("NETPLANNER_CSRF_ENABLED", "0")
os.environ.setdefault("SESSION_COOKIE_SECURE", "false")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-do-not-use-in-production")

from collections.abc import AsyncGenerator  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import models  # noqa: E402, F401  (registers tables on Base.metadata)
from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import auth_service  # noqa: E402

# Ensure the cached Settings picks up the test env vars.
get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session bound to a fresh in-memory database per test."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def auth_user(db_session: AsyncSession) -> User:
    """Create a user for the test and return the ORM record."""
    return await auth_service.create_user(
        db_session,
        email="primary@netplanner.test",
        password="correct horse battery staple",
    )


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    """A second user — used by cross-user authorization tests."""
    return await auth_service.create_user(
        db_session,
        email="secondary@netplanner.test",
        password="correct horse battery staple",
    )


@pytest_asyncio.fixture
async def anon_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """Yield an unauthenticated HTTP client (no session cookie attached)."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, auth_user: User
) -> AsyncGenerator[AsyncClient, None]:
    """Yield an authenticated HTTP client whose cookie is the auth_user's JWT."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    settings = get_settings()
    token = auth_service.issue_session_token(auth_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={settings.session_cookie_name: token},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def second_client(
    db_session: AsyncSession, second_user: User
) -> AsyncGenerator[AsyncClient, None]:
    """Yield an authenticated client for `second_user` — for cross-user tests."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    settings = get_settings()
    token = auth_service.issue_session_token(second_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={settings.session_cookie_name: token},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
