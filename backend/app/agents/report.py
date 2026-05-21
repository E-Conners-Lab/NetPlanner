"""Report Agent (PIS-11) — assembles a project's artifacts into report HTML.

Like the TCO Agent, this is **deterministic** templating, not an LLM call.
PIS-05 requires the PDF to render every table and figure "without truncation
or formatting errors", and a report must never hallucinate a number — so the
document is assembled reproducibly from the already-computed artifacts. The
narrative content is the artifacts' own text (the Advisor's answers, a
comparison's summary, a TCO's assumptions); the report does not generate new
prose.

Every report carries the mandatory disclaimer (PIS-23, PIS-24 #4).
"""

from __future__ import annotations

import datetime as dt
from html import escape

import markdown as md

from app.models.comparison import VendorComparison
from app.models.conversation import Message
from app.models.project import Project
from app.models.tco import TCOScenario

# Mandatory footer on every export — not optional (PIS-24 #4).
REPORT_DISCLAIMER = (
    "NetPlanner outputs are estimates for planning purposes only. All pricing "
    "should be verified directly with vendors before formal budget submission."
)

_CONFIDENCE_CLASS = {
    "confirmed": "conf-confirmed",
    "estimated": "conf-estimated",
    "unavailable": "conf-unavailable",
}

# TCO breakdown columns in render order (bottom-up of the stacked chart).
# A column is rendered only when at least one year carries a non-zero value, so
# simple scenarios keep a compact table and detailed scenarios get the full
# breakdown introduced in PID amendment 1.3.
_TCO_COLUMNS: list[tuple[str, str]] = [
    ("hardware", "Hardware"),
    ("spares", "Spares"),
    ("accessories", "Accessories"),
    ("installation", "Installation"),
    ("training", "Training"),
    ("licensing", "Licensing"),
    ("support", "Support (Y1)"),
    ("support_recurring", "Support (recur)"),
    ("adjacent_recurring", "Adjacent recur"),
]

# Light, print-friendly stylesheet. The amber accent ties to the brand; the
# document itself is white for printing/PDF.
_STYLESHEET = """
@page {
  size: letter; margin: 2cm;
  @bottom-center {
    content: "NetPlanner — planning estimates only · page " counter(page);
    font-size: 8pt; color: #999;
  }
}
body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1A1D27;
       font-size: 11pt; line-height: 1.5; }
h1 { font-size: 20pt; margin: 0 0 2px; }
h2 { font-size: 14pt; margin: 26px 0 8px; border-bottom: 2px solid #F59E0B;
     padding-bottom: 3px; }
h3 { font-size: 11.5pt; margin: 14px 0 4px; }
.report-header { border-bottom: 3px solid #F59E0B; padding-bottom: 10px;
                 margin-bottom: 8px; }
.muted { color: #6B7280; font-size: 9.5pt; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 10pt; }
th, td { border: 1px solid #D6D8DF; padding: 5px 9px; text-align: left;
         vertical-align: top; }
th { background: #F4F4F6; font-weight: 600; }
.num { font-family: 'JetBrains Mono', 'Courier New', monospace;
       text-align: right; white-space: nowrap; }
.total-row td { font-weight: 700; background: #FFF8EB; }
.bar-track { background: #ECECEF; border-radius: 2px; height: 14px; width: 100%; }
.bar-fill { background: #F59E0B; height: 14px; border-radius: 2px; }
.conf-confirmed { color: #15803D; font-weight: 600; }
.conf-estimated { color: #B45309; font-weight: 600; }
.conf-unavailable { color: #9099A6; font-weight: 600; }
.cell-source { font-size: 8pt; color: #6B7280; word-break: break-all; }
.advisor-msg { margin: 8px 0; }
.advisor-role { font-weight: 700; font-size: 9pt; text-transform: uppercase;
                color: #6B7280; }
.notice { border: 1px solid #D6D8DF; background: #F8F8FA; padding: 8px 12px;
          font-size: 9.5pt; color: #6B7280; margin: 8px 0; }
.disclaimer { margin-top: 34px; border: 1px solid #F59E0B; background: #FFF8EB;
              padding: 12px 14px; font-size: 9pt; color: #555; }
.assumptions { font-size: 9.5pt; color: #555; }
"""


def _money(value: float | int) -> str:
    """Format a number as a whole-dollar currency string."""
    return f"${value:,.0f}"


def _render_header(project: Project, title: str) -> str:
    today = dt.date.today().isoformat()
    company = f" · {escape(project.company)}" if project.company else ""
    return (
        '<div class="report-header">'
        f"<h1>{escape(title)}</h1>"
        f'<p class="muted">{escape(project.name)}{company} · generated {today}'
        "</p></div>"
    )


def _render_project_overview(project: Project) -> str:
    budget = (
        _money(project.budget_ceiling)
        if project.budget_ceiling is not None
        else "not specified"
    )
    rows = [
        ("Company", project.company or "—"),
        ("Description", project.description or "—"),
        ("Existing infrastructure", project.existing_infra or "—"),
        ("Budget ceiling", budget),
    ]
    body = "".join(
        f"<tr><th>{escape(label)}</th><td>{escape(str(value))}</td></tr>"
        for label, value in rows
    )
    return f"<h2>Project Overview</h2><table>{body}</table>"


def _render_tco(scenario: TCOScenario) -> str:
    years: list[dict] = list(scenario.year_by_year)
    totals = [float(y.get("total", 0)) for y in years] or [0.0]
    peak = max(totals) or 1.0

    # Show only categories that carry a non-zero value in any year — keeps
    # simple scenarios compact while still exposing the PID 1.3 categories
    # when they're actually used.
    active_columns = [
        (key, label)
        for key, label in _TCO_COLUMNS
        if any(float(year.get(key, 0) or 0) > 0 for year in years)
    ]

    def _cell(value: float) -> str:
        return f"<td class='num'>{_money(value)}</td>"

    rows = []
    for year in years:
        pct = float(year.get("total", 0)) / peak * 100
        cells = "".join(
            _cell(float(year.get(key, 0) or 0)) for key, _ in active_columns
        )
        rows.append(
            "<tr>"
            f"<td>Year {escape(str(year.get('year', '')))}</td>"
            f"{cells}"
            f"<td class='num'>{_money(year.get('total', 0))}</td>"
            f"<td><div class='bar-track'><div class='bar-fill' "
            f"style='width:{pct:.1f}%'></div></div></td>"
            "</tr>"
        )

    blank_cells = "<td class='num'></td>" * len(active_columns)
    total_row = (
        f"<tr class='total-row'><td>{scenario.inputs.get('lifecycle_years', 5)}-year "
        f"total</td>{blank_cells}"
        f"<td class='num'>{_money(scenario.total_5yr)}</td><td></td></tr>"
    )

    column_headers = "".join(f"<th>{escape(label)}</th>" for _, label in active_columns)
    assumptions = "".join(f"<li>{escape(str(a))}</li>" for a in scenario.assumptions)
    warnings = "".join(f"<li>{escape(str(w))}</li>" for w in scenario.warnings)
    warning_block = (
        f"<h3>Reasonableness warnings</h3><ul class='assumptions'>{warnings}</ul>"
        if warnings
        else ""
    )

    return (
        f"<h2>TCO Scenario — {escape(scenario.scenario_name)}</h2>"
        f"<table><thead><tr><th>Period</th>{column_headers}"
        "<th>Total</th><th>Relative cost</th></tr></thead>"
        f"<tbody>{''.join(rows)}{total_row}</tbody></table>"
        f"<h3>Assumptions</h3><ul class='assumptions'>{assumptions}</ul>"
        f"{warning_block}"
    )


def _render_comparison(comparison: VendorComparison) -> str:
    vendors: list[str] = list(comparison.vendors)
    criteria: list[str] = list(comparison.criteria)
    matrix: dict = comparison.matrix

    header = "".join(f"<th>{escape(v)}</th>" for v in vendors)
    rows = []
    for criterion in criteria:
        cells = []
        for vendor in vendors:
            cell = matrix.get(vendor, {}).get(criterion, {})
            confidence = str(cell.get("confidence", "unavailable"))
            css = _CONFIDENCE_CLASS.get(confidence, "conf-unavailable")
            source = str(cell.get("source", ""))
            source_html = (
                f"<div class='cell-source'>{escape(source)}</div>" if source else ""
            )
            cells.append(
                f"<td>{escape(str(cell.get('value', '—')))}"
                f"<div class='{css}'>{escape(confidence)}</div>"
                f"{source_html}</td>"
            )
        rows.append(f"<tr><th>{escape(criterion)}</th>{''.join(cells)}</tr>")

    return (
        f"<h2>Vendor Comparison — {escape(' vs '.join(vendors))}</h2>"
        f"<table><thead><tr><th>Criterion</th>{header}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        f"<h3>Summary</h3><p>{escape(comparison.summary)}</p>"
    )


def _render_advisor(title: str, messages: list[Message]) -> str:
    blocks = []
    for message in messages:
        role = "Advisor" if message.role == "assistant" else "You"
        if message.role == "assistant":
            # The Advisor replies in markdown — render it to HTML.
            content = md.markdown(message.content, extensions=["tables", "sane_lists"])
        else:
            content = f"<p>{escape(message.content)}</p>"
        blocks.append(
            f"<div class='advisor-msg'><div class='advisor-role'>{escape(role)}"
            f"</div>{content}</div>"
        )
    return f"<h2>Advisor Summary — {escape(title)}</h2>{''.join(blocks)}"


def render_report(
    project: Project,
    tco_scenarios: list[TCOScenario],
    comparisons: list[VendorComparison],
    advisor_sections: list[tuple[str, list[Message]]],
    unresolved: list[str],
) -> str:
    """Assemble a project's artifacts into a complete report HTML document.

    Args:
        project: The project being reported on.
        tco_scenarios: Saved TCO scenarios to include.
        comparisons: Saved vendor comparisons to include.
        advisor_sections: ``(conversation title, messages)`` pairs.
        unresolved: Descriptions of requested artifacts that could not be
            resolved — surfaced as an explicit notice rather than dropped
            silently (PIS-20).

    Returns:
        str: A complete HTML document ready for the WeasyPrint PDF service.
    """
    sections = [_render_project_overview(project)]
    sections += [_render_tco(s) for s in tco_scenarios]
    sections += [_render_comparison(c) for c in comparisons]
    sections += [_render_advisor(title, msgs) for title, msgs in advisor_sections]

    if unresolved:
        items = "".join(f"<li>{escape(u)}</li>" for u in unresolved)
        sections.append(
            "<h2>Notice</h2><div class='notice'>The following requested items "
            f"could not be included:<ul>{items}</ul></div>"
        )

    body = "".join(sections)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<style>{_STYLESHEET}</style></head><body>"
        f"{_render_header(project, f'NetPlanner Report — {project.name}')}"
        f"{body}"
        f"<div class='disclaimer'>{escape(REPORT_DISCLAIMER)}</div>"
        "</body></html>"
    )
