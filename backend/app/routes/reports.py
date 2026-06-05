"""Report routes.

`POST` assembles the requested artifacts into HTML (Report Agent), renders a
PDF (WeasyPrint), records the export, and returns the PDF as a download. `GET`
lists a project's export history. `GET .../pdf` returns the original PDF
bytes — every report is stored as an immutable snapshot at create time so a
re-download yields exactly the artifact that was originally generated (the
TCO numbers a finance reviewer signed off on never silently change underneath
them).
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.report import render_report
from app.auth import get_current_user
from app.database import get_db
from app.models.report import Report
from app.models.user import User
from app.rate_limit import limiter, rate_limit
from app.schemas.report import ReportRead, ReportRequest
from app.services import pdf, project_service, report_service

router = APIRouter(prefix="/projects", tags=["reports"])


def _filename(title: str) -> str:
    """Build a safe PDF filename from a report title."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower() or "report"
    return f"{slug[:60]}.pdf"


@router.post("/{project_id}/reports")
@limiter.limit(rate_limit("report_create"))
async def create_report(
    request: Request,
    project_id: str,
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Generate a PDF report for a project and return it as a download."""
    project = await project_service.get_project(db, project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    (
        tco_scenarios,
        comparisons,
        advisor_sections,
        tco_comparisons,
        unresolved,
    ) = await report_service.resolve_artifacts(db, project_id, payload.artifacts)
    html = render_report(
        project,
        tco_scenarios,
        comparisons,
        advisor_sections,
        unresolved,
        tco_comparisons,
        title=payload.title,
    )
    pdf_bytes = await pdf.generate_pdf(html)

    # Persist an immutable snapshot — the bytes themselves, not just metadata.
    # Re-downloads return these bytes verbatim so a previously-shared report
    # never silently changes.
    await report_service.save_report(
        db, project_id, payload.title, payload.artifacts, pdf_bytes
    )

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
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Report]:
    """List a project's generated-report history, newest first."""
    project = await project_service.get_project(db, project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await report_service.list_reports(db, project_id)


@router.get("/{project_id}/reports/{report_id}/pdf")
@limiter.limit(rate_limit("report_download"))
async def download_report(
    request: Request,
    project_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Return a previously-generated report as a PDF download.

    The original PDF bytes are returned verbatim from the immutable snapshot
    stored at create time — the historical artifact never silently changes
    if the underlying TCO or comparison rows are edited or deleted.

    Cross-project access is rejected with 404 rather than 403 to avoid
    leaking the existence of reports the caller cannot read (SEC-27).
    """
    project = await project_service.get_project(db, project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    report = await report_service.get_report(db, report_id)
    if report is None or report.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Report not found")

    pdf_bytes = await report_service.load_report_pdf(report)
    if pdf_bytes is None:
        raise HTTPException(
            status.HTTP_410_GONE, detail="Report archive is no longer available"
        )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{_filename(report.title)}"',
            # SEC-24 — the PDF carries project data; never cache it.
            "Cache-Control": "no-store",
        },
    )
