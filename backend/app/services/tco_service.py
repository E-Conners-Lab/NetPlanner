"""TCO scenario persistence.

A scenario is persisted only on an explicit save (PIS-25). The server always
recomputes the model from the inputs (SEC-05) — client-supplied year-by-year
figures are never trusted.

Versioning (PID amendment 1.5): `save_scenario` accepts an optional `parent`
scenario. When supplied, the new row inherits the parent's `lineage_id` and
takes `version = max(version in lineage) + 1`. When absent, the new row starts
a fresh lineage (`lineage_id = own id`, `version = 1`).

Concurrent saves to the same lineage are guarded at two layers:
1. A unique `(lineage_id, version)` DB constraint (migration ab4c8a31bc1a).
2. A short retry loop in this module so a race-loser refreshes the
   `max(version)` query and tries again instead of bubbling a 500 to the UI.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import new_uuid
from app.models.tco import TCOScenario
from app.schemas.tco import TCOResult

_MAX_VERSION_RETRIES = 5


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

    If two requests race to save the same next version, the DB's unique
    constraint rejects the loser; we re-read the current max version and
    retry with a bumped number (capped at `_MAX_VERSION_RETRIES`).
    """
    if parent is None:
        # Fresh lineage — generate the id up-front so we can use it as the
        # lineage_id, keeping the v1 row self-referential. A fresh-lineage
        # save cannot race against a concurrent save because the id is
        # globally unique.
        scenario_id = new_uuid()
        return await _persist(
            db,
            project_id,
            result,
            scenario_id=scenario_id,
            lineage_id=scenario_id,
            version=1,
        )

    lineage_id = parent.lineage_id
    for attempt in range(_MAX_VERSION_RETRIES):
        next_version = await _next_version(db, lineage_id)
        try:
            return await _persist(
                db,
                project_id,
                result,
                scenario_id=new_uuid(),
                lineage_id=lineage_id,
                version=next_version,
            )
        except IntegrityError:
            await db.rollback()
            if attempt == _MAX_VERSION_RETRIES - 1:
                raise
            # Brief backoff so the racing transaction commits its winning row
            # before we re-read max(version).
            await asyncio.sleep(0.02 * (attempt + 1))

    # Unreachable — the loop above either returns or raises.
    raise RuntimeError("TCO scenario save retry budget exhausted")


async def _next_version(db: AsyncSession, lineage_id: str) -> int:
    """Return max(version)+1 for the lineage (1-indexed if the lineage is empty)."""
    row = await db.execute(
        select(func.max(TCOScenario.version)).where(
            TCOScenario.lineage_id == lineage_id
        )
    )
    return (row.scalar() or 0) + 1


async def _persist(
    db: AsyncSession,
    project_id: str,
    result: TCOResult,
    *,
    scenario_id: str,
    lineage_id: str,
    version: int,
) -> TCOScenario:
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
