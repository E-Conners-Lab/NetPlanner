"""Vendor Comparison routes — generate/save and list saved comparisons.

Phase-0 stubs. The comparison matrix and confidence handling land with the
Comparison Agent in Phase 4.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.comparison import ComparisonRequest

router = APIRouter(prefix="/projects", tags=["comparison"])

_NOT_IMPLEMENTED = {"status": "not implemented"}


@router.post("/{project_id}/comparison", status_code=status.HTTP_201_CREATED)
async def create_comparison(
    project_id: str,
    payload: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate and save a vendor comparison. Implemented in Phase 4."""
    return _NOT_IMPLEMENTED


@router.get("/{project_id}/comparison")
async def list_comparisons(project_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """List saved vendor comparisons for a project. Implemented in Phase 4."""
    return _NOT_IMPLEMENTED
