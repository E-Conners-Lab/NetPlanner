"""Tests for the auth layer (register / login / logout / me) and SEC-02 gate."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.models.user import User


async def test_register_sets_session_cookie(anon_client: AsyncClient) -> None:
    resp = await anon_client.post(
        "/api/auth/register",
        json={"email": "new@netplanner.test", "password": "correct horse battery"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "new@netplanner.test"
    assert get_settings().session_cookie_name in resp.cookies


async def test_register_rejects_duplicate_email(
    anon_client: AsyncClient, auth_user: User
) -> None:
    resp = await anon_client.post(
        "/api/auth/register",
        json={"email": auth_user.email, "password": "correct horse battery"},
    )
    assert resp.status_code == 409


async def test_register_rejects_short_password(anon_client: AsyncClient) -> None:
    resp = await anon_client.post(
        "/api/auth/register",
        json={"email": "x@example.com", "password": "short"},
    )
    assert resp.status_code == 422


async def test_login_with_wrong_password_returns_generic_401(
    anon_client: AsyncClient, auth_user: User
) -> None:
    resp = await anon_client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": "wrong"},
    )
    assert resp.status_code == 401
    # SEC-18 — generic message, no enumeration distinction.
    assert "invalid" in resp.json()["detail"].lower()


async def test_login_with_unknown_email_returns_generic_401(
    anon_client: AsyncClient,
) -> None:
    resp = await anon_client.post(
        "/api/auth/login",
        json={"email": "nobody@netplanner.test", "password": "anything anything"},
    )
    assert resp.status_code == 401


async def test_login_success_issues_new_session_cookie(
    anon_client: AsyncClient, auth_user: User
) -> None:
    resp = await anon_client.post(
        "/api/auth/login",
        json={
            "email": auth_user.email,
            "password": "correct horse battery staple",
        },
    )
    assert resp.status_code == 200
    assert get_settings().session_cookie_name in resp.cookies


async def test_account_locks_after_five_failed_logins(
    anon_client: AsyncClient, auth_user: User
) -> None:
    # Five consecutive wrong passwords trip the lockout (SEC-06).
    for _ in range(5):
        resp = await anon_client.post(
            "/api/auth/login",
            json={"email": auth_user.email, "password": "wrong"},
        )
        assert resp.status_code == 401

    # Even the correct password is now rejected, with the same generic message
    # (SEC-18 — the lockout is not revealed to a probing caller).
    locked = await anon_client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": "correct horse battery staple"},
    )
    assert locked.status_code == 401
    assert "invalid" in locked.json()["detail"].lower()


async def test_successful_login_resets_failed_count(
    anon_client: AsyncClient, auth_user: User
) -> None:
    # Four failures (below the threshold) then a success clears the counter.
    for _ in range(4):
        await anon_client.post(
            "/api/auth/login",
            json={"email": auth_user.email, "password": "wrong"},
        )
    ok = await anon_client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": "correct horse battery staple"},
    )
    assert ok.status_code == 200

    # The counter was reset, so four more failures still do not lock the
    # account — a fifth consecutive failure would be required.
    for _ in range(4):
        resp = await anon_client.post(
            "/api/auth/login",
            json={"email": auth_user.email, "password": "wrong"},
        )
        assert resp.status_code == 401
    still_ok = await anon_client.post(
        "/api/auth/login",
        json={"email": auth_user.email, "password": "correct horse battery staple"},
    )
    assert still_ok.status_code == 200


async def test_me_requires_authentication(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/auth/me")
    assert resp.status_code == 401


async def test_logout_invalidates_existing_tokens(
    client: AsyncClient, auth_user: User
) -> None:
    # The fixture-issued cookie is valid until logout bumps session_version.
    me_first = await client.get("/api/auth/me")
    assert me_first.status_code == 200

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 204

    # The same cookie no longer authenticates the user.
    me_after = await client.get("/api/auth/me")
    assert me_after.status_code == 401


async def test_unauthenticated_caller_cannot_list_projects(
    anon_client: AsyncClient,
) -> None:
    resp = await anon_client.get("/api/projects")
    assert resp.status_code == 401


async def test_unauthenticated_caller_cannot_create_project(
    anon_client: AsyncClient,
) -> None:
    resp = await anon_client.post("/api/projects", json={"name": "X"})
    assert resp.status_code == 401


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/projects/x"),
        ("PUT", "/api/projects/x"),
        ("DELETE", "/api/projects/x"),
        ("POST", "/api/projects/x/advisor"),
        ("GET", "/api/projects/x/conversations"),
        ("POST", "/api/projects/x/tco"),
        ("GET", "/api/projects/x/tco"),
        ("POST", "/api/projects/x/tco/preview"),
        ("POST", "/api/projects/x/comparison"),
        ("GET", "/api/projects/x/comparison"),
        ("POST", "/api/projects/x/reports"),
        ("GET", "/api/projects/x/reports"),
    ],
)
async def test_every_project_route_requires_authentication(
    anon_client: AsyncClient, method: str, path: str
) -> None:
    resp = await anon_client.request(method, path, json={})
    assert resp.status_code == 401, f"{method} {path} should require auth"
