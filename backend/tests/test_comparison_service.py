"""Integration tests for the vendor comparison persistence service (PIS-25)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.comparison import ComparisonCell, ComparisonResult
from app.services import comparison_service


async def _make_project(db: AsyncSession) -> Project:
    project = Project(name="Comparison Test Project")
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


def _sample_result() -> ComparisonResult:
    return ComparisonResult(
        vendors=["Cisco Meraki", "Juniper Mist"],
        criteria=["licensing model"],
        matrix={
            "Cisco Meraki": {
                "licensing model": ComparisonCell(
                    value="Subscription",
                    source="https://meraki.com",
                    confidence="confirmed",
                )
            },
            "Juniper Mist": {
                "licensing model": ComparisonCell(
                    value="Subscription", source="", confidence="estimated"
                )
            },
        },
        summary="Both vendors use subscription licensing.",
    )


async def test_save_and_get_comparison(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)

    saved = await comparison_service.save_comparison(
        db_session, project.id, _sample_result()
    )

    assert saved.id
    assert saved.vendors == ["Cisco Meraki", "Juniper Mist"]
    assert saved.matrix["Cisco Meraki"]["licensing model"]["confidence"] == "confirmed"

    fetched = await comparison_service.get_comparison(db_session, saved.id)
    assert fetched is not None
    assert fetched.id == saved.id


async def test_get_comparison_missing_returns_none(db_session: AsyncSession) -> None:
    assert await comparison_service.get_comparison(db_session, "missing") is None


async def test_list_comparisons(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    await comparison_service.save_comparison(db_session, project.id, _sample_result())
    await comparison_service.save_comparison(db_session, project.id, _sample_result())

    comparisons = await comparison_service.list_comparisons(db_session, project.id)
    assert len(comparisons) == 2
