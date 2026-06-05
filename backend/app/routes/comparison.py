"""Vendor Comparison routes.

`POST` generates a comparison: the Research Agent runs once per vendor
(PIS-12), then the Comparison Agent synthesizes the matrix in a single call
(PIS-13), and the result is saved. `GET` lists saved comparisons.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.comparison import run_comparison_agent
from app.agents.project_context import build_project_context
from app.agents.research import research
from app.auth import get_current_user
from app.database import get_db
from app.models.comparison import VendorComparison
from app.models.user import User
from app.rate_limit import limiter, rate_limit
from app.schemas.comparison import ComparisonRequest, VendorComparisonRead
from app.services import comparison_service, project_service

router = APIRouter(prefix="/projects", tags=["comparison"])


def _research_query(vendor: str) -> str:
    """Build the research query for one vendor.

    Focused on pricing — that is the data that genuinely needs a live source.
    Non-pricing criteria (licensing model, API, AI/ML) are stable product
    facts the Comparison Agent fills from its own knowledge.
    """
    return f"{vendor} wireless access point list price and per-AP annual licensing cost"


@router.post(
    "/{project_id}/comparison",
    response_model=VendorComparisonRead,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(rate_limit("comparison"))
async def create_comparison(
    request: Request,
    project_id: str,
    payload: ComparisonRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VendorComparison:
    """Generate and save a vendor comparison matrix."""
    project = await project_service.get_project(db, project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    context = await build_project_context(project)
    # PIS-12: Research feeds Comparison. Run the per-vendor searches in parallel.
    research_data = list(
        await asyncio.gather(
            *(research(_research_query(vendor)) for vendor in payload.vendors)
        )
    )
    result = await run_comparison_agent(
        payload.vendors, payload.criteria, research_data, context
    )
    return await comparison_service.save_comparison(db, project_id, result)


@router.get("/{project_id}/comparison", response_model=list[VendorComparisonRead])
async def list_comparisons(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VendorComparison]:
    """List a project's saved vendor comparisons, newest first."""
    project = await project_service.get_project(db, project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await comparison_service.list_comparisons(db, project_id)
