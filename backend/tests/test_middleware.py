"""Tests for the security-headers middleware (SEC-08, SEC-10, SEC-25)."""

from __future__ import annotations

from httpx import AsyncClient

from app.config import get_settings


async def test_security_headers_present_on_responses(client: AsyncClient) -> None:
    resp = await client.get("/api/projects")

    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    # Deny-all CSP on the API origin (SEC-09).
    assert resp.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
    )
    # API JSON is session-bound — never cache it (SEC-24).
    assert resp.headers["cache-control"] == "no-store"
    # HSTS is opt-in (HTTPS-only); off by default in dev / tests.
    assert "strict-transport-security" not in resp.headers


async def test_hsts_header_emitted_when_enabled(client: AsyncClient) -> None:
    settings = get_settings()
    settings.enable_hsts = True
    try:
        resp = await client.get("/api/projects")
        assert "max-age=31536000" in resp.headers["strict-transport-security"]
    finally:
        settings.enable_hsts = False


async def test_hsts_header_emitted_in_production(client: AsyncClient) -> None:
    # Production sends HSTS automatically, even without ENABLE_HSTS (SEC-08).
    settings = get_settings()
    settings.environment = "production"
    try:
        resp = await client.get("/api/projects")
        assert "max-age=31536000" in resp.headers["strict-transport-security"]
    finally:
        settings.environment = "development"


async def test_security_headers_do_not_override_route_headers(
    client: AsyncClient,
) -> None:
    # The advisor SSE route sets Cache-Control: no-store (SEC-24). The
    # middleware uses setdefault, so it must not clobber that.
    project = (await client.post("/api/projects", json={"name": "Hdr test"})).json()
    resp = await client.post(
        f"/api/projects/{project['id']}/advisor", json={"message": "hi"}
    )

    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["x-frame-options"] == "DENY"
