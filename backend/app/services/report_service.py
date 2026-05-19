"""Report persistence and artifact resolution.

`resolve_artifacts` turns the requested `ReportArtifact` references into the
actual saved objects, verifying each belongs to the project (SEC-27). An
artifact that cannot be resolved is reported as an "unresolved" notice rather
than dropped silently — the report is still produced (PIS-20).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comparison import VendorComparison
from app.models.conversation import Message
from app.models.report import Report
from app.models.tco import TCOScenario
from app.schemas.report import ReportArtifact
from app.services import comparison_service, conversation_service, tco_service

# Resolved artifacts: TCO scenarios, comparisons, (conversation title, messages)
# pairs, and human-readable descriptions of anything that could not be resolved.
ResolvedArtifacts = tuple[
    list[TCOScenario],
    list[VendorComparison],
    list[tuple[str, list[Message]]],
    list[str],
]


async def resolve_artifacts(
    db: AsyncSession, project_id: str, artifacts: list[ReportArtifact]
) -> ResolvedArtifacts:
    """Resolve report artifact references to saved objects for one project."""
    tco_scenarios: list[TCOScenario] = []
    comparisons: list[VendorComparison] = []
    advisor_sections: list[tuple[str, list[Message]]] = []
    unresolved: list[str] = []

    for artifact in artifacts:
        if artifact.kind == "tco":
            scenario = await tco_service.get_scenario(db, artifact.ref_id)
            if scenario is not None and scenario.project_id == project_id:
                tco_scenarios.append(scenario)
            else:
                unresolved.append(f"TCO scenario {artifact.ref_id} (not found)")
        elif artifact.kind == "comparison":
            comparison = await comparison_service.get_comparison(db, artifact.ref_id)
            if comparison is not None and comparison.project_id == project_id:
                comparisons.append(comparison)
            else:
                unresolved.append(f"Comparison {artifact.ref_id} (not found)")
        elif artifact.kind == "advisor_summary":
            conversation = await conversation_service.get_conversation(
                db, artifact.ref_id
            )
            if conversation is not None and conversation.project_id == project_id:
                messages = await conversation_service.list_messages(db, conversation.id)
                advisor_sections.append((conversation.title, messages))
            else:
                unresolved.append(f"Advisor conversation {artifact.ref_id} (not found)")

    return tco_scenarios, comparisons, advisor_sections, unresolved


async def save_report(
    db: AsyncSession, project_id: str, title: str, artifacts: list[ReportArtifact]
) -> Report:
    """Persist metadata for a generated report (export history)."""
    report = Report(
        project_id=project_id,
        title=title,
        included_artifacts=[a.model_dump() for a in artifacts],
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def list_reports(db: AsyncSession, project_id: str) -> list[Report]:
    """Return a project's generated-report history, newest first."""
    result = await db.execute(
        select(Report)
        .where(Report.project_id == project_id)
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())
