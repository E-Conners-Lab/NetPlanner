"""Server-side validation: max-length / count limits across the schemas (SEC-05)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.schemas.comparison import ComparisonRequest
from app.schemas.conversation import AdvisorRequest
from app.schemas.project import ProjectCreate
from app.schemas.report import ReportArtifact, ReportRequest
from app.schemas.tco import TCOFormInputs


def test_project_description_too_long_rejected() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", description="a" * 4001)


def test_project_existing_infra_too_long_rejected() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", existing_infra="a" * 4001)


def test_project_budget_ceiling_overflow_rejected() -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(name="x", budget_ceiling=10**13)


def test_advisor_message_too_long_rejected() -> None:
    with pytest.raises(ValidationError):
        AdvisorRequest(message="x" * 4001)


def test_comparison_vendor_name_too_long_rejected() -> None:
    with pytest.raises(ValidationError):
        ComparisonRequest(vendors=["A" * 121, "B"], criteria=["licensing"])


def test_comparison_criterion_too_long_rejected() -> None:
    with pytest.raises(ValidationError):
        ComparisonRequest(vendors=["A", "B"], criteria=["x" * 201])


def test_comparison_too_many_criteria_rejected() -> None:
    with pytest.raises(ValidationError):
        ComparisonRequest(vendors=["A", "B"], criteria=[f"crit-{i}" for i in range(11)])


def test_report_too_many_artifacts_rejected() -> None:
    with pytest.raises(ValidationError):
        ReportRequest(
            title="X",
            artifacts=[ReportArtifact(kind="tco", ref_id=f"id-{i}") for i in range(21)],
        )


def test_tco_device_count_overflow_rejected() -> None:
    with pytest.raises(ValidationError):
        TCOFormInputs(
            device_count=10_000_001,
            hardware_cost_per_unit=600,
            licensing_cost_per_unit_year=98,
        )


def test_tco_hardware_cost_overflow_rejected() -> None:
    with pytest.raises(ValidationError):
        TCOFormInputs(
            device_count=10,
            hardware_cost_per_unit=10**10,
            licensing_cost_per_unit_year=98,
        )


def test_tco_too_many_refresh_events_rejected() -> None:
    with pytest.raises(ValidationError):
        TCOFormInputs(
            device_count=10,
            hardware_cost_per_unit=600,
            licensing_cost_per_unit_year=98,
            refresh_events=[{"year": 2, "percent_of_devices": 5} for _ in range(11)],
        )


async def test_route_rejects_oversize_project_description(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/api/projects", json={"name": "x", "description": "a" * 4001}
    )
    assert resp.status_code == 422


async def test_route_rejects_oversize_advisor_message(
    client: AsyncClient,
) -> None:
    project = (await client.post("/api/projects", json={"name": "Big"})).json()
    resp = await client.post(
        f"/api/projects/{project['id']}/advisor",
        json={"message": "x" * 4001},
    )
    assert resp.status_code == 422
