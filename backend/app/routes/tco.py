"""TCO Calculator routes.

`preview` computes a model without saving — letting the UI surface
reasonableness warnings (PIS-21) before the user commits. `POST /tco` computes
and saves. Incomplete input is rejected by the `TCOFormInputs` schema with a
422 (Eval 4 / PIS-04) — financial inputs are never silently defaulted.

Versioning (PID amendment 1.5): a `POST` may include `parent_scenario_id` in
the payload to save the result as the next version of an existing lineage.
The convenience `GET /lineages/{lineage_id}` route returns every version in a
lineage for the version history UI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tco import calculate_tco
from app.database import get_db
from app.models.tco import TCOScenario
from app.schemas.tco import TCOResult, TCOScenarioCreate, TCOScenarioRead
from app.services import project_service, tco_service

router = APIRouter(prefix="/projects", tags=["tco"])


async def _require_project(db: AsyncSession, project_id: str) -> None:
    """Raise 404 if the project does not exist."""
    if await project_service.get_project(db, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _resolve_parent(
    db: AsyncSession, project_id: str, parent_scenario_id: str | None
) -> TCOScenario | None:
    """Resolve and authorize a parent scenario reference (SEC-27).

    Cross-project access is rejected as 404 rather than 403 so we never confirm
    that a scenario the caller isn't allowed to read exists.
    """
    if parent_scenario_id is None:
        return None
    parent = await tco_service.get_scenario(db, parent_scenario_id)
    if parent is None or parent.project_id != project_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail="Parent scenario not found"
        )
    return parent


@router.post("/{project_id}/tco/preview", response_model=TCOResult)
async def preview_tco(
    project_id: str,
    payload: TCOScenarioCreate,
    db: AsyncSession = Depends(get_db),
) -> TCOResult:
    """Compute a TCO model without saving it — for review before committing."""
    await _require_project(db, project_id)
    return calculate_tco(payload.scenario_name, payload.inputs)


@router.post(
    "/{project_id}/tco",
    response_model=TCOScenarioRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_tco_scenario(
    project_id: str,
    payload: TCOScenarioCreate,
    db: AsyncSession = Depends(get_db),
) -> TCOScenario:
    """Compute and persist a TCO scenario.

    If `parent_scenario_id` is supplied, the saved row joins that scenario's
    lineage as the next version. Otherwise a fresh lineage starts at v1.
    """
    await _require_project(db, project_id)
    parent = await _resolve_parent(db, project_id, payload.parent_scenario_id)
    result = calculate_tco(payload.scenario_name, payload.inputs)
    return await tco_service.save_scenario(db, project_id, result, parent=parent)


@router.get("/{project_id}/tco", response_model=list[TCOScenarioRead])
async def list_tco_scenarios(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[TCOScenario]:
    """List a project's saved TCO scenarios, newest first."""
    await _require_project(db, project_id)
    return await tco_service.list_scenarios(db, project_id)


@router.get(
    "/{project_id}/tco/lineages/{lineage_id}",
    response_model=list[TCOScenarioRead],
)
async def list_tco_lineage_versions(
    project_id: str,
    lineage_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[TCOScenario]:
    """Return every version in a lineage for one project (oldest first).

    Empty list is a valid response when the lineage_id is unknown — we do not
    expose whether it exists in another project (SEC-27).
    """
    await _require_project(db, project_id)
    return await tco_service.list_versions(db, project_id, lineage_id)
