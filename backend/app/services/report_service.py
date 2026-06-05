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
# pairs, TCO-scenario comparison pairs (PID amendment 1.5), and human-readable
# descriptions of anything that could not be resolved.
ResolvedArtifacts = tuple[
    list[TCOScenario],
    list[VendorComparison],
    list[tuple[str, list[Message]]],
    list[tuple[TCOScenario, TCOScenario]],
    list[str],
]


async def resolve_artifacts(
    db: AsyncSession, project_id: str, artifacts: list[ReportArtifact]
) -> ResolvedArtifacts:
    """Resolve report artifact references to saved objects for one project."""
    tco_scenarios: list[TCOScenario] = []
    comparisons: list[VendorComparison] = []
    advisor_sections: list[tuple[str, list[Message]]] = []
    tco_comparisons: list[tuple[TCOScenario, TCOScenario]] = []
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
        elif artifact.kind == "tco_comparison":
            scenario_a = await tco_service.get_scenario(db, artifact.ref_id)
            scenario_b = (
                await tco_service.get_scenario(db, artifact.ref_id_b)
                if artifact.ref_id_b
                else None
            )
            both_resolved = (
                scenario_a is not None
                and scenario_b is not None
                and scenario_a.project_id == project_id
                and scenario_b.project_id == project_id
            )
            if both_resolved:
                # Type checker sees the None-narrowing through `both_resolved`.
                assert scenario_a is not None and scenario_b is not None
                tco_comparisons.append((scenario_a, scenario_b))
            else:
                unresolved.append(
                    f"TCO comparison {artifact.ref_id} vs "
                    f"{artifact.ref_id_b} (not found)"
                )

    return (
        tco_scenarios,
        comparisons,
        advisor_sections,
        tco_comparisons,
        unresolved,
    )


async def save_report(
    db: AsyncSession,
    project_id: str,
    title: str,
    artifacts: list[ReportArtifact],
    pdf_bytes: bytes | None = None,
) -> Report:
    """Persist a generated report and its immutable PDF snapshot.

    `pdf_bytes` is the authoritative artifact for re-downloads; the artifact
    references are kept alongside it as audit history (what was included) and
    are no longer re-resolved on read.
    """
    report = Report(
        project_id=project_id,
        title=title,
        included_artifacts=[a.model_dump() for a in artifacts],
        pdf_blob=pdf_bytes,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def load_report_pdf(report: Report) -> bytes | None:
    """Return the immutable PDF bytes for a saved report, or ``None``.

    Bytes live in `pdf_blob` for reports created since the immutable-snapshot
    rollout. The `file_path` fallback handles a future move-to-disk storage
    backend; if both are empty, the snapshot is no longer recoverable and
    the route layer returns 410 Gone.
    """
    if report.pdf_blob is not None:
        return bytes(report.pdf_blob)
    if report.file_path:
        try:
            with open(report.file_path, "rb") as handle:
                return handle.read()
        except OSError:
            return None
    return None


async def list_reports(db: AsyncSession, project_id: str) -> list[Report]:
    """Return a project's generated-report history, newest first."""
    result = await db.execute(
        select(Report)
        .where(Report.project_id == project_id)
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars().all())


async def get_report(db: AsyncSession, report_id: str) -> Report | None:
    """Fetch one report by id, or None if it does not exist."""
    result = await db.execute(select(Report).where(Report.id == report_id))
    return result.scalar_one_or_none()
