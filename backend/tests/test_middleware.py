"""Tests for the security-headers middleware (SEC-08, SEC-10, SEC-25)."""

from __future__ import annotations

from httpx import AsyncClient


async def test_security_headers_present_on_responses(client: AsyncClient) -> None:
    resp = await client.get("/api/projects")

    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "max-age=31536000" in resp.headers["strict-transport-security"]


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
