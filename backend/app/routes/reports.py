"""Report routes.

`POST` assembles the requested artifacts into HTML (Report Agent), renders a
PDF (WeasyPrint), records the export, and returns the PDF as a download. `GET`
lists a project's export history. `GET .../pdf` re-renders and returns a
previously-generated report by id — the artifact references are deterministic
so the same artifacts always produce the same PDF.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.report import render_report
from app.database import get_db
from app.models.report import Report
from app.schemas.report import ReportArtifact, ReportRead, ReportRequest
from app.services import pdf, project_service, report_service

router = APIRouter(prefix="/projects", tags=["reports"])


def _filename(title: str) -> str:
    """Build a safe PDF filename from a report title."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower() or "report"
    return f"{slug[:60]}.pdf"


@router.post("/{project_id}/reports")
async def create_report(
    project_id: str,
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate a PDF report for a project and return it as a download."""
    project = await project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    tco_scenarios, comparisons, advisor_sections, unresolved = (
        await report_service.resolve_artifacts(db, project_id, payload.artifacts)
    )
    html = render_report(
        project, tco_scenarios, comparisons, advisor_sections, unresolved
    )
    pdf_bytes = await pdf.generate_pdf(html)

    # Record the export for history (PIS-28 audit-style trail).
    await report_service.save_report(db, project_id, payload.title, payload.artifacts)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(payload.title)}"',
            # SEC-24 — the PDF carries project data; never cache it.
            "Cache-Control": "no-store",
        },
    )


@router.get("/{project_id}/reports", response_model=list[ReportRead])
async def list_reports(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[Report]:
    """List a project's generated-report history, newest first."""
    project = await project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await report_service.list_reports(db, project_id)


@router.get("/{project_id}/reports/{report_id}/pdf")
async def download_report(
    project_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Re-render and return a previously-generated report as a PDF download.

    The report's stored `included_artifacts` are re-resolved against current
    data and re-rendered. Because TCO scenarios and comparisons are immutable
    after save, the output matches what was originally exported as long as
    the referenced artifacts still exist (unresolved ones surface as a notice
    in the report, per PIS-20).

    Cross-project access is rejected with 404 rather than 403 to avoid
    leaking the existence of reports the caller cannot read (SEC-27).
    """
    project = await project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    report = await report_service.get_report(db, report_id)
    if report is None or report.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")

    artifacts = [ReportArtifact(**a) for a in report.included_artifacts]
    tco_scenarios, comparisons, advisor_sections, unresolved = (
        await report_service.resolve_artifacts(db, project_id, artifacts)
    )
    html = render_report(
        project, tco_scenarios, comparisons, advisor_sections, unresolved
    )
    pdf_bytes = await pdf.generate_pdf(html)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(report.title)}"',
            # SEC-24 — the PDF carries project data; never cache it.
            "Cache-Control": "no-store",
        },
    )
