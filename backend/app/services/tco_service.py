"""TCO scenario persistence.

A scenario is persisted only on an explicit save (PIS-25). The server always
recomputes the model from the inputs (SEC-05) — client-supplied year-by-year
figures are never trusted.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tco import TCOScenario
from app.schemas.tco import TCOResult


async def save_scenario(
    db: AsyncSession, project_id: str, result: TCOResult
) -> TCOScenario:
    """Persist a computed TCO result as a saved scenario for a project."""
    scenario = TCOScenario(
        project_id=project_id,
        scenario_name=result.scenario_name,
        inputs=result.inputs.model_dump(),
        year_by_year=[year.model_dump() for year in result.year_by_year],
        total_5yr=result.total_5yr,
        assumptions=list(result.assumptions),
        warnings=list(result.warnings),
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


async def get_scenario(db: AsyncSession, scenario_id: str) -> TCOScenario | None:
    """Return a TCO scenario by id, or ``None`` if it does not exist."""
    return await db.get(TCOScenario, scenario_id)
