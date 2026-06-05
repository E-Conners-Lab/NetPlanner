"""Tests for the double-submit CSRF protection (SEC-07).

The wider suite runs with ``NETPLANNER_CSRF_ENABLED=0`` (set in conftest) so
behavior tests are not forced to thread a token through every POST. These
tests opt enforcement back on and exercise the middleware directly.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.models.user import User

_CORRECT_PASSWORD = "correct horse battery staple"


@pytest.fixture
def csrf_on(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable CSRF enforcement for the duration of a test."""
    monkeypatch.setenv("NETPLANNER_CSRF_ENABLED", "1")


async def test_safe_get_seeds_csrf_cookie(
    anon_client: AsyncClient, csrf_on: None
) -> None:
    settings = get_settings()
    resp = await anon_client.get("/api/auth/csrf")
    assert resp.status_code == 204
    assert settings.csrf_cookie_name in resp.cookies


async def test_mutating_request_without_token_is_forbidden(
    anon_client: AsyncClient, csrf_on: None, auth_user: User
) -> None:
    resp = await anon_client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": _CORRECT_PASSWORD},
    )
    assert resp.status_code == 403
    assert "csrf" in resp.json()["detail"].lower()


async def test_mutating_request_with_mismatched_token_is_forbidden(
    anon_client: AsyncClient, csrf_on: None, auth_user: User
) -> None:
    settings = get_settings()
    await anon_client.get("/api/auth/csrf")  # seed the cookie in the jar
    resp = await anon_client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": _CORRECT_PASSWORD},
        headers={settings.csrf_header_name: "not-the-real-token"},
    )
    assert resp.status_code == 403


async def test_mutating_request_with_matching_token_passes(
    anon_client: AsyncClient, csrf_on: None, auth_user: User
) -> None:
    settings = get_settings()
    seed = await anon_client.get("/api/auth/csrf")
    token = seed.cookies[settings.csrf_cookie_name]
    resp = await anon_client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": _CORRECT_PASSWORD},
        headers={settings.csrf_header_name: token},
    )
    assert resp.status_code == 200
