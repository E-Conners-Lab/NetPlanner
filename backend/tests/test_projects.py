"""Integration tests for the Projects CRUD API (Phase 1).

Covers the happy paths plus server-side validation (SEC-05) and 404 handling.
"""

from __future__ import annotations

from httpx import AsyncClient

_VALID_PROJECT = {
    "name": "Campus Wi-Fi Refresh",
    "company": "Acme Corp",
    "description": "Replace aging APs across 3 buildings.",
    "existing_infra": "200 legacy 802.11ac APs, Cisco WLC.",
    "budget_ceiling": 250000.0,
}


# --- Create -----------------------------------------------------------------


async def test_create_project_returns_201_and_resource(client: AsyncClient) -> None:
    resp = await client.post("/api/projects", json=_VALID_PROJECT)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == _VALID_PROJECT["name"]
    assert body["budget_ceiling"] == 250000.0
    assert body["id"]
    assert body["created_at"] and body["updated_at"]


async def test_create_project_minimal_only_name(client: AsyncClient) -> None:
    resp = await client.post("/api/projects", json={"name": "Minimal"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Minimal"
    assert body["company"] == ""
    assert body["budget_ceiling"] is None


async def test_create_project_rejects_missing_name(client: AsyncClient) -> None:
    # SEC-05: server-side validation, regardless of frontend checks.
    resp = await client.post("/api/projects", json={"company": "Acme"})
    assert resp.status_code == 422


async def test_create_project_rejects_blank_name(client: AsyncClient) -> None:
    resp = await client.post("/api/projects", json={"name": ""})
    assert resp.status_code == 422


async def test_create_project_rejects_negative_budget(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/projects", json={"name": "Bad budget", "budget_ceiling": -1}
    )
    assert resp.status_code == 422


# --- List -------------------------------------------------------------------


async def test_list_projects_empty(client: AsyncClient) -> None:
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_projects_returns_created(client: AsyncClient) -> None:
    await client.post("/api/projects", json={"name": "First"})
    await client.post("/api/projects", json={"name": "Second"})
    resp = await client.get("/api/projects")
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert names == {"First", "Second"}


# --- Get --------------------------------------------------------------------


async def test_get_project_found(client: AsyncClient) -> None:
    created = (await client.post("/api/projects", json=_VALID_PROJECT)).json()
    resp = await client.get(f"/api/projects/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_project_not_found_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/api/projects/does-not-exist")
    assert resp.status_code == 404
    # SEC-11: generic message, no internal details leaked.
    assert resp.json()["detail"] == "Project not found"


# --- Update -----------------------------------------------------------------


async def test_update_project_full(client: AsyncClient) -> None:
    created = (await client.post("/api/projects", json=_VALID_PROJECT)).json()
    resp = await client.put(
        f"/api/projects/{created['id']}",
        json={"name": "Renamed", "budget_ceiling": 99999.0},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Renamed"
    assert body["budget_ceiling"] == 99999.0


async def test_update_project_partial_preserves_other_fields(
    client: AsyncClient,
) -> None:
    created = (await client.post("/api/projects", json=_VALID_PROJECT)).json()
    resp = await client.put(
        f"/api/projects/{created['id']}", json={"description": "Updated desc only"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["description"] == "Updated desc only"
    # Untouched fields are preserved.
    assert body["name"] == _VALID_PROJECT["name"]
    assert body["company"] == _VALID_PROJECT["company"]


async def test_update_project_not_found_returns_404(client: AsyncClient) -> None:
    resp = await client.put("/api/projects/missing", json={"name": "x"})
    assert resp.status_code == 404


async def test_update_project_rejects_negative_budget(client: AsyncClient) -> None:
    created = (await client.post("/api/projects", json=_VALID_PROJECT)).json()
    resp = await client.put(
        f"/api/projects/{created['id']}", json={"budget_ceiling": -5}
    )
    assert resp.status_code == 422


# --- Delete -----------------------------------------------------------------


async def test_delete_project_returns_204(client: AsyncClient) -> None:
    created = (await client.post("/api/projects", json=_VALID_PROJECT)).json()
    resp = await client.delete(f"/api/projects/{created['id']}")
    assert resp.status_code == 204


async def test_delete_project_not_found_returns_404(client: AsyncClient) -> None:
    resp = await client.delete("/api/projects/missing")
    assert resp.status_code == 404


async def test_delete_project_then_get_returns_404(client: AsyncClient) -> None:
    created = (await client.post("/api/projects", json=_VALID_PROJECT)).json()
    await client.delete(f"/api/projects/{created['id']}")
    resp = await client.get(f"/api/projects/{created['id']}")
    assert resp.status_code == 404
