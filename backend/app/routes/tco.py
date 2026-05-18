"""TCO Calculator routes — compute/save and list saved scenarios.

Phase-0 stubs. The reasonableness check (PIS-21) and incomplete-input gate
(Eval 4 / PIS-04) land with the TCO Agent in Phase 3.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.tco import TCOScenarioCreate

router = APIRouter(prefix="/projects", tags=["tco"])

_NOT_IMPLEMENTED = {"status": "not implemented"}


@router.post("/{project_id}/tco", status_code=status.HTTP_201_CREATED)
async def create_tco_scenario(
    project_id: str,
    payload: TCOScenarioCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Compute and save a TCO scenario. Implemented in Phase 3."""
    return _NOT_IMPLEMENTED


@router.get("/{project_id}/tco")
async def list_tco_scenarios(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> dict:
    """List saved TCO scenarios for a project. Implemented in Phase 3."""
    return _NOT_IMPLEMENTED
