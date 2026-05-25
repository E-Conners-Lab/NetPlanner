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


# ---------------------------------------------------------------------------
# PID amendment 1.5 — versioning (lineage_id + version)
# ---------------------------------------------------------------------------


async def test_fresh_save_starts_new_lineage_at_v1(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)

    saved = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("V1", _INPUTS)
    )

    # No parent → new lineage anchored to the row's own id, version 1.
    assert saved.version == 1
    assert saved.lineage_id == saved.id


async def test_save_with_parent_inherits_lineage_and_bumps_version(
    db_session: AsyncSession,
) -> None:
    project = await _make_project(db_session)

    v1 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Refresh plan", _INPUTS)
    )
    v2 = await tco_service.save_scenario(
        db_session,
        project.id,
        calculate_tco("Refresh plan", _INPUTS),
        parent=v1,
    )
    v3 = await tco_service.save_scenario(
        db_session,
        project.id,
        calculate_tco("Refresh plan", _INPUTS),
        parent=v2,
    )

    # All three share the same lineage_id (the id of v1).
    assert v1.lineage_id == v2.lineage_id == v3.lineage_id == v1.id
    # And versions are strictly increasing.
    assert (v1.version, v2.version, v3.version) == (1, 2, 3)
    # Distinct row identities.
    assert len({v1.id, v2.id, v3.id}) == 3


async def test_branching_from_v1_still_bumps_past_existing_max(
    db_session: AsyncSession,
) -> None:
    """A second branch from v1 produces v3 (max+1), not v2 — versions are
    monotonic within a lineage even when the user branches off an older version."""
    project = await _make_project(db_session)

    v1 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Lineage", _INPUTS)
    )
    v2 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Lineage", _INPUTS), parent=v1
    )
    branched = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Lineage", _INPUTS), parent=v1
    )

    assert v2.version == 2
    assert branched.version == 3
    assert branched.lineage_id == v1.lineage_id


async def test_list_versions_returns_lineage_oldest_first(
    db_session: AsyncSession,
) -> None:
    project = await _make_project(db_session)
    v1 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Plan", _INPUTS)
    )
    v2 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Plan", _INPUTS), parent=v1
    )

    # A second, unrelated lineage in the same project — must not leak in.
    other = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("Unrelated", _INPUTS)
    )

    history = await tco_service.list_versions(db_session, project.id, v1.lineage_id)
    assert [row.id for row in history] == [v1.id, v2.id]
    assert other.id not in {row.id for row in history}


async def test_list_versions_is_scoped_to_project(db_session: AsyncSession) -> None:
    """Asking for a lineage that exists in a different project returns []."""
    project_a = await _make_project(db_session)
    project_b = await _make_project(db_session)

    v1_a = await tco_service.save_scenario(
        db_session, project_a.id, calculate_tco("A", _INPUTS)
    )

    cross = await tco_service.list_versions(db_session, project_b.id, v1_a.lineage_id)
    assert cross == []
