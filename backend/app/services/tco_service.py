"""TCO scenario persistence.

A scenario is persisted only on an explicit save (PIS-25). The server always
recomputes the model from the inputs (SEC-05) — client-supplied year-by-year
figures are never trusted.

Versioning (PID amendment 1.5): `save_scenario` accepts an optional `parent`
scenario. When supplied, the new row inherits the parent's `lineage_id` and
takes `version = max(version in lineage) + 1`. When absent, the new row starts
a fresh lineage (`lineage_id = own id`, `version = 1`).
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import new_uuid
from app.models.tco import TCOScenario
from app.schemas.tco import TCOResult


async def save_scenario(
    db: AsyncSession,
    project_id: str,
    result: TCOResult,
    parent: TCOScenario | None = None,
) -> TCOScenario:
    """Persist a computed TCO result as a saved scenario for a project.

    When `parent` is provided, the new row joins the parent's lineage as the
    next version. The caller is responsible for verifying the parent belongs
    to the same project (SEC-27) — the route layer does that check.
    """
    if parent is None:
        # Fresh lineage — generate the id up-front so we can use it as the
        # lineage_id, keeping the v1 row self-referential.
        scenario_id = new_uuid()
        lineage_id = scenario_id
        version = 1
    else:
        scenario_id = new_uuid()
        lineage_id = parent.lineage_id
        # Highest existing version in this lineage + 1. Concurrent saves to
        # the same lineage are vanishingly rare in this single-user app; if
        # that ever changes, switch to a unique (lineage_id, version) index.
        next_version_row = await db.execute(
            select(func.max(TCOScenario.version)).where(
                TCOScenario.lineage_id == lineage_id
            )
        )
        version = (next_version_row.scalar() or 0) + 1

    scenario = TCOScenario(
        id=scenario_id,
        project_id=project_id,
        scenario_name=result.scenario_name,
        inputs=result.inputs.model_dump(),
        year_by_year=[year.model_dump() for year in result.year_by_year],
        total_5yr=result.total_5yr,
        assumptions=list(result.assumptions),
        warnings=list(result.warnings),
        lineage_id=lineage_id,
        version=version,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return scenario


async def list_scenarios(db: AsyncSession, project_id: str) -> list[TCOScenario]:
    """Return a project's saved TCO scenarios, newest first."""
    result = await db.execute(
        select(TCOScenario)
        .where(TCOScenario.project_id == project_id)
        .order_by(TCOScenario.created_at.desc())
    )
    return list(result.scalars().all())


async def list_versions(
    db: AsyncSession, project_id: str, lineage_id: str
) -> list[TCOScenario]:
    """Return every version in a lineage for a project, oldest first.

    Scoped to `project_id` so a caller cannot enumerate another project's
    lineage by guessing its id (SEC-27).
    """
    result = await db.execute(
        select(TCOScenario)
        .where(
            TCOScenario.project_id == project_id,
            TCOScenario.lineage_id == lineage_id,
        )
        .order_by(TCOScenario.version.asc())
    )
    return list(result.scalars().all())


async def get_scenario(db: AsyncSession, scenario_id: str) -> TCOScenario | None:
    """Return a TCO scenario by id, or ``None`` if it does not exist."""
    return await db.get(TCOScenario, scenario_id)
