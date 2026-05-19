"""Vendor comparison persistence.

A comparison is persisted on generation (PIS-25). The matrix is stored as
plain JSON matching the Comparison -> Report handoff contract (PIS-15).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comparison import VendorComparison
from app.schemas.comparison import ComparisonResult


async def save_comparison(
    db: AsyncSession, project_id: str, result: ComparisonResult
) -> VendorComparison:
    """Persist a generated comparison result for a project."""
    comparison = VendorComparison(
        project_id=project_id,
        vendors=list(result.vendors),
        criteria=list(result.criteria),
        matrix={
            vendor: {criterion: cell.model_dump() for criterion, cell in row.items()}
            for vendor, row in result.matrix.items()
        },
        summary=result.summary,
    )
    db.add(comparison)
    await db.commit()
    await db.refresh(comparison)
    return comparison


async def list_comparisons(db: AsyncSession, project_id: str) -> list[VendorComparison]:
    """Return a project's saved comparisons, newest first."""
    result = await db.execute(
        select(VendorComparison)
        .where(VendorComparison.project_id == project_id)
        .order_by(VendorComparison.created_at.desc())
    )
    return list(result.scalars().all())


async def get_comparison(
    db: AsyncSession, comparison_id: str
) -> VendorComparison | None:
    """Return a comparison by id, or ``None`` if it does not exist."""
    return await db.get(VendorComparison, comparison_id)
