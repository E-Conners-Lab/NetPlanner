"""Cross-user authorization tests (SEC-03 / SEC-27).

A project — and every artifact under it — is owned by its creator. Another
authenticated user cannot read, modify, or delete it, and ownership tests
return ``404`` (not ``403``) so the existence of a project owned by another
user is not leaked through error differentiation.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _create_project_owned_by(client: AsyncClient, name: str) -> dict:
    resp = await client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_second_user_cannot_see_others_projects_in_list(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    await _create_project_owned_by(client, "Private")

    resp = await second_client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_second_user_gets_404_on_other_users_project(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    project = await _create_project_owned_by(client, "Private")

    resp = await second_client.get(f"/api/projects/{project['id']}")
    assert resp.status_code == 404


async def test_second_user_cannot_update_other_users_project(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    project = await _create_project_owned_by(client, "Private")

    resp = await second_client.put(
        f"/api/projects/{project['id']}", json={"name": "Hijacked"}
    )
    assert resp.status_code == 404

    # The original is untouched.
    me = await client.get(f"/api/projects/{project['id']}")
    assert me.json()["name"] == "Private"


async def test_second_user_cannot_delete_other_users_project(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    project = await _create_project_owned_by(client, "Private")

    resp = await second_client.delete(f"/api/projects/{project['id']}")
    assert resp.status_code == 404

    me = await client.get(f"/api/projects/{project['id']}")
    assert me.status_code == 200


@pytest.mark.parametrize(
    "path_template",
    [
        "/api/projects/{id}/tco",
        "/api/projects/{id}/comparison",
        "/api/projects/{id}/conversations",
        "/api/projects/{id}/reports",
    ],
)
async def test_second_user_cannot_access_project_subresources(
    client: AsyncClient, second_client: AsyncClient, path_template: str
) -> None:
    project = await _create_project_owned_by(client, "Private")

    resp = await second_client.get(path_template.format(id=project["id"]))
    assert resp.status_code == 404


async def test_second_user_advisor_post_cross_project_404(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    project = await _create_project_owned_by(client, "Private")

    resp = await second_client.post(
        f"/api/projects/{project['id']}/advisor",
        json={"message": "hi from someone else"},
    )
    assert resp.status_code == 404


async def test_tco_save_cross_user_returns_404(
    client: AsyncClient, second_client: AsyncClient
) -> None:
    project = await _create_project_owned_by(client, "Private")
    body = {
        "scenario_name": "X",
        "inputs": {
            "device_count": 10,
            "hardware_cost_per_unit": 600,
            "licensing_cost_per_unit_year": 100,
        },
    }

    resp = await second_client.post(f"/api/projects/{project['id']}/tco", json=body)
    assert resp.status_code == 404
