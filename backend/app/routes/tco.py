"""TCO Calculator routes.

`preview` computes a model without saving — letting the UI surface
reasonableness warnings (PIS-21) before the user commits. `POST /tco` computes
and saves. Incomplete input is rejected by the `TCOFormInputs` schema with a
422 (Eval 4 / PIS-04) — financial inputs are never silently defaulted.
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
    """Compute and persist a TCO scenario."""
    await _require_project(db, project_id)
    result = calculate_tco(payload.scenario_name, payload.inputs)
    return await tco_service.save_scenario(db, project_id, result)


@router.get("/{project_id}/tco", response_model=list[TCOScenarioRead])
async def list_tco_scenarios(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[TCOScenario]:
    """List a project's saved TCO scenarios, newest first."""
    await _require_project(db, project_id)
    return await tco_service.list_scenarios(db, project_id)
