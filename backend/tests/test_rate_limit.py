"""Tests for the rate limiter (SEC-06).

The suite-wide fixture disables rate limiting so behavior tests stay fast.
These tests opt back in by manually enabling the SlowAPI limiter, exercise
the cap, and disable it again on cleanup.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.database import get_db
from app.main import app
from app.models.user import User
from app.rate_limit import limiter
from app.services import auth_service


@pytest_asyncio.fixture
async def rate_limited_client(
    db_session, auth_user: User
) -> AsyncIterator[AsyncClient]:
    """An authenticated client with the limiter forcibly enabled."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    settings = get_settings()
    token = auth_service.issue_session_token(auth_user)

    # SlowAPI exposes an `enabled` attribute on the Limiter — flip it on for
    # this fixture and reset on teardown so other tests stay unaffected.
    prior = limiter.enabled
    limiter.enabled = True
    # Reset SlowAPI's internal storage so a previous test's count does not
    # bleed into this test's window.
    limiter.reset()

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            cookies={settings.session_cookie_name: token},
        ) as ac:
            yield ac
    finally:
        limiter.enabled = prior
        limiter.reset()
        app.dependency_overrides.clear()


async def test_advisor_returns_429_after_burst(
    rate_limited_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Advisor is capped at 10/min — the 11th call gets a 429."""

    async def _fake_turn(history, context, summary=None):
        yield "ok"

    monkeypatch.setattr("app.routes.advisor.stream_advisor_turn", _fake_turn)

    project = (
        await rate_limited_client.post(
            "/api/projects",
            json={"name": "Burst", "description": "200 APs."},
        )
    ).json()
    url = f"/api/projects/{project['id']}/advisor"
    body = {"message": "Justify the spend."}

    statuses: list[int] = []
    for _ in range(12):
        statuses.append((await rate_limited_client.post(url, json=body)).status_code)

    assert 429 in statuses, statuses
    # And the 429 carries the structured retry hint.
    last_blocked = next(s for s in statuses if s == 429)
    assert last_blocked == 429


async def test_login_returns_429_after_burst(
    rate_limited_client: AsyncClient, auth_user: User
) -> None:
    """Login is capped at 10/min for an anonymous IP — the burst gets a 429.

    Guards against the decorator being dropped (SEC-06): the limit config
    existed but was never wired to the auth routes, leaving credential
    stuffing uncapped. Cookies are cleared each call so the limiter keys on
    the caller IP — the credential-stuffing threat model.
    """
    statuses: list[int] = []
    for _ in range(12):
        rate_limited_client.cookies.clear()
        resp = await rate_limited_client.post(
            "/api/auth/login",
            json={"email": auth_user.email, "password": "wrong-password"},
        )
        statuses.append(resp.status_code)

    assert 429 in statuses, statuses


async def test_register_returns_429_after_burst(
    rate_limited_client: AsyncClient,
) -> None:
    """Registration is capped at 5/min for an anonymous IP (signup spam)."""
    statuses: list[int] = []
    for i in range(7):
        rate_limited_client.cookies.clear()
        resp = await rate_limited_client.post(
            "/api/auth/register",
            json={
                "email": f"burst{i}@netplanner.test",
                "password": "correct horse battery",
            },
        )
        statuses.append(resp.status_code)

    assert 429 in statuses, statuses
