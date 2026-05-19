"""Integration tests for report artifact resolution and persistence."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tco import calculate_tco
from app.models.project import Project
from app.schemas.comparison import ComparisonCell, ComparisonResult
from app.schemas.report import ReportArtifact
from app.schemas.tco import TCOFormInputs
from app.services import (
    comparison_service,
    conversation_service,
    report_service,
    tco_service,
)

_TCO_INPUTS = TCOFormInputs(
    device_count=10, hardware_cost_per_unit=600, licensing_cost_per_unit_year=100
)


async def _project(db: AsyncSession, name: str = "Report Test") -> Project:
    project = Project(name=name)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


def _comparison_result() -> ComparisonResult:
    return ComparisonResult(
        vendors=["A", "B"],
        criteria=["c"],
        matrix={
            "A": {"c": ComparisonCell(value="x", source="", confidence="estimated")},
            "B": {"c": ComparisonCell(value="y", source="", confidence="estimated")},
        },
        summary="s",
    )


async def test_resolve_artifacts_resolves_each_kind(db_session: AsyncSession) -> None:
    project = await _project(db_session)
    tco = await tco_service.save_scenario(
        db_session, project.id, calculate_tco("S", _TCO_INPUTS)
    )
    comparison = await comparison_service.save_comparison(
        db_session, project.id, _comparison_result()
    )
    conversation = await conversation_service.create_conversation(
        db_session, project.id, "CFO chat"
    )
    await conversation_service.add_message(db_session, conversation.id, "user", "hi")

    artifacts = [
        ReportArtifact(kind="tco", ref_id=tco.id),
        ReportArtifact(kind="comparison", ref_id=comparison.id),
        ReportArtifact(kind="advisor_summary", ref_id=conversation.id),
    ]
    tcos, comparisons, advisors, unresolved = await report_service.resolve_artifacts(
        db_session, project.id, artifacts
    )

    assert len(tcos) == 1
    assert len(comparisons) == 1
    assert len(advisors) == 1
    assert advisors[0][0] == "CFO chat"
    assert unresolved == []


async def test_resolve_artifacts_flags_missing(db_session: AsyncSession) -> None:
    # PIS-20: an unresolved artifact is surfaced, not silently dropped.
    project = await _project(db_session)
    tcos, _, _, unresolved = await report_service.resolve_artifacts(
        db_session, project.id, [ReportArtifact(kind="tco", ref_id="nope")]
    )
    assert tcos == []
    assert len(unresolved) == 1


async def test_resolve_artifacts_rejects_cross_project(
    db_session: AsyncSession,
) -> None:
    # SEC-27: an artifact owned by another project is not resolved.
    project_a = await _project(db_session, "Project A")
    project_b = await _project(db_session, "Project B")
    tco = await tco_service.save_scenario(
        db_session, project_a.id, calculate_tco("S", _TCO_INPUTS)
    )

    tcos, _, _, unresolved = await report_service.resolve_artifacts(
        db_session, project_b.id, [ReportArtifact(kind="tco", ref_id=tco.id)]
    )
    assert tcos == []
    assert len(unresolved) == 1


async def test_save_and_list_reports(db_session: AsyncSession) -> None:
    project = await _project(db_session)
    await report_service.save_report(
        db_session, project.id, "Q1 Report", [ReportArtifact(kind="tco", ref_id="x")]
    )

    reports = await report_service.list_reports(db_session, project.id)
    assert len(reports) == 1
    assert reports[0].title == "Q1 Report"
