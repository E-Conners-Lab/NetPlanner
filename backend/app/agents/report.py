"""Report Agent (PIS-11).

Model: ``claude-sonnet-4-5`` — formatting and narrative generation (PIS-29).
Renders a project plus its selected artifacts into an HTML string for
WeasyPrint.

Every report MUST carry the mandatory disclaimer footer (PIS-23, PIS-24 #4):
"NetPlanner outputs are estimates for planning purposes only. All pricing
should be verified directly with vendors before formal budget submission."
"""

from __future__ import annotations

from app.models.project import Project

# Mandatory footer on every export — not optional (PIS-24 #4).
REPORT_DISCLAIMER = (
    "NetPlanner outputs are estimates for planning purposes only. All pricing "
    "should be verified directly with vendors before formal budget submission."
)


async def render_report(project: Project, artifacts: list[dict]) -> str:
    """Render a project and its artifacts into a report HTML string.

    Args:
        project: The project being reported on.
        artifacts: Resolved artifacts — TCO results, comparison matrices,
            and/or advisor conversation summaries.

    Returns:
        str: An HTML document, including the mandatory disclaimer footer,
        ready for the WeasyPrint PDF service.

    Raises:
        NotImplementedError: Always — implemented in Phase 5.
    """
    raise NotImplementedError("Report Agent — implemented in Phase 5")
