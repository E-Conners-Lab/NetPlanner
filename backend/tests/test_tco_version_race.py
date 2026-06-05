"""Concurrent TCO version saves end up with monotonic distinct versions."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tco import calculate_tco
from app.models.project import Project
from app.models.tco import TCOScenario
from app.models.user import User
from app.schemas.tco import TCOFormInputs
from app.services import tco_service

_INPUTS = TCOFormInputs(
    device_count=10,
    hardware_cost_per_unit=600,
    licensing_cost_per_unit_year=100,
)


async def test_unique_lineage_version_constraint_blocks_duplicate_inserts(
    db_session: AsyncSession, auth_user: User
) -> None:
    """DB-level guard — two rows with the same (lineage_id, version) cannot coexist."""
    project = Project(name="Race", owner_id=auth_user.id)
    db_session.add(project)
    await db_session.commit()

    v1 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("v1", _INPUTS)
    )

    # Manually try to insert a duplicate (lineage_id, version=1) — should fail.
    dup = TCOScenario(
        id="duplicate-id",
        project_id=project.id,
        scenario_name="dup",
        inputs={},
        year_by_year=[],
        total_5yr=0.0,
        assumptions=[],
        warnings=[],
        lineage_id=v1.lineage_id,
        version=1,
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_retry_on_version_collision_produces_distinct_versions(
    db_session: AsyncSession, auth_user: User
) -> None:
    """Two saves that *would* collide each end up with a unique version.

    With the production retry loop in `save_scenario`, the loser of a race
    re-reads `max(version)+1` and tries again. We simulate that by saving
    serially — the test exists to assert correctness of the retry path, not
    actual parallelism (SQLite + asyncpg pooled connections would be needed
    for a true concurrency test).
    """
    project = Project(name="Race", owner_id=auth_user.id)
    db_session.add(project)
    await db_session.commit()

    v1 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("plan", _INPUTS)
    )
    # Two children of v1 — second one must retry past version=2.
    a = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("plan", _INPUTS), parent=v1
    )
    b = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("plan", _INPUTS), parent=v1
    )

    assert {a.version, b.version} == {2, 3}
    assert a.lineage_id == b.lineage_id == v1.lineage_id


async def test_collision_with_simulated_race_uses_retry_path(
    db_session: AsyncSession, auth_user: User
) -> None:
    """If the first attempt collides on (lineage_id, version), retry bumps version.

    We simulate the race by inserting a v2 row out-of-band right before the
    service's next `save_scenario(parent=v1)` call. With the retry loop, the
    service hits IntegrityError, rolls back, re-reads `max(version)`, and
    succeeds with v3 — not v2.
    """
    project = Project(name="Race", owner_id=auth_user.id)
    db_session.add(project)
    await db_session.commit()

    v1 = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("plan", _INPUTS)
    )

    # Out-of-band v2 (e.g. another worker beat us to it).
    intruder = TCOScenario(
        id="intruder-id",
        project_id=project.id,
        scenario_name="other worker v2",
        inputs={},
        year_by_year=[],
        total_5yr=0.0,
        assumptions=[],
        warnings=[],
        lineage_id=v1.lineage_id,
        version=2,
    )
    db_session.add(intruder)
    await db_session.commit()

    # The service's retry must land us on v3, not collide.
    saved = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("plan", _INPUTS), parent=v1
    )
    assert saved.version == 3
