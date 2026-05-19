"""Integration tests for the TCO scenario persistence service (PIS-25)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tco import calculate_tco
from app.models.project import Project
from app.schemas.tco import TCOFormInputs
from app.services import tco_service

_INPUTS = TCOFormInputs(
    device_count=200,
    hardware_cost_per_unit=600,
    licensing_cost_per_unit_year=98,
)


async def _make_project(db: AsyncSession) -> Project:
    project = Project(name="TCO Test Project")
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def test_save_and_get_scenario(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)

    saved = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("AP Refresh", _INPUTS)
    )

    assert saved.id
    assert saved.scenario_name == "AP Refresh"
    assert saved.total_5yr == 218_000

    fetched = await tco_service.get_scenario(db_session, saved.id)
    assert fetched is not None
    assert fetched.id == saved.id


async def test_get_scenario_missing_returns_none(db_session: AsyncSession) -> None:
    assert await tco_service.get_scenario(db_session, "does-not-exist") is None


async def test_list_scenarios(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Scenario A", _INPUTS)
    )
    await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Scenario B", _INPUTS)
    )

    scenarios = await tco_service.list_scenarios(db_session, project.id)
    assert {s.scenario_name for s in scenarios} == {"Scenario A", "Scenario B"}


async def test_saved_scenario_persists_full_breakdown(
    db_session: AsyncSession,
) -> None:
    project = await _make_project(db_session)

    saved = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Breakdown", _INPUTS)
    )

    assert len(saved.year_by_year) == 5
    assert saved.year_by_year[0]["total"] == 139_600
    assert saved.assumptions
    assert saved.warnings == []
