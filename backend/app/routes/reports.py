"""Report routes — generate a downloadable PDF export.

Phase-0 stub. In Phase 5 the POST handler returns the rendered PDF (the
mandatory disclaimer footer per PIS-24 #4 is enforced by the Report Agent).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.report import ReportRequest

router = APIRouter(prefix="/projects", tags=["reports"])


@router.post("/{project_id}/reports", status_code=status.HTTP_201_CREATED)
async def create_report(
    project_id: str,
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a PDF report for a project. Implemented in Phase 5."""
    return {"status": "not implemented"}
