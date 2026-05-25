"""Unit tests for the Report Agent — HTML assembly (PIS-05, PIS-20, PIS-24)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.agents.report import REPORT_DISCLAIMER, render_report
from app.models.comparison import VendorComparison
from app.models.conversation import Message
from app.models.project import Project
from app.models.tco import TCOScenario

_PROJECT = Project(
    name="Campus Refresh",
    company="Acme Corp",
    description="200-AP refresh.",
    existing_infra="Legacy APs.",
    budget_ceiling=480000.0,
)


def _tco(
    scenario_id: str = "scenario-1",
    name: str = "AP Refresh",
    lineage_id: str | None = None,
    version: int = 1,
    total: float = 218000.0,
    year_one_total: float = 139600.0,
    year_two_total: float = 19600.0,
) -> TCOScenario:
    return TCOScenario(
        id=scenario_id,
        scenario_name=name,
        inputs={},
        year_by_year=[
            {
                "year": 1,
                "hardware": year_one_total - 19600 if year_one_total >= 19600 else 0,
                "licensing": 19600,
                "support": 0,
                "total": year_one_total,
            },
            {
                "year": 2,
                "hardware": 0,
                "licensing": 19600,
                "support": 0,
                "total": year_two_total,
            },
        ],
        total_5yr=total,
        assumptions=["Hardware is a one-time Year-1 cost."],
        warnings=[],
        lineage_id=lineage_id or scenario_id,
        version=version,
        created_at=datetime(2026, 5, 25, tzinfo=UTC),
    )


def _comparison() -> VendorComparison:
    return VendorComparison(
        vendors=["Cisco Meraki", "Juniper Mist"],
        criteria=["licensing model"],
        matrix={
            "Cisco Meraki": {
                "licensing model": {
                    "value": "Subscription",
                    "source": "https://meraki.com",
                    "confidence": "confirmed",
                }
            },
            "Juniper Mist": {
                "licensing model": {
                    "value": "Subscription",
                    "source": "",
                    "confidence": "estimated",
                }
            },
        },
        summary="Both vendors use subscription licensing.",
    )


def test_report_is_html_with_mandatory_disclaimer() -> None:
    html = render_report(_PROJECT, [], [], [], [])
    assert html.startswith("<!DOCTYPE html>")
    assert REPORT_DISCLAIMER in html  # PIS-24 #4 — on every export
    assert "Campus Refresh" in html


def test_report_renders_tco_scenario() -> None:
    html = render_report(_PROJECT, [_tco()], [], [], [])
    assert "AP Refresh" in html
    assert "$218,000" in html
    assert "$139,600" in html
    assert "Hardware is a one-time Year-1 cost." in html


def test_report_renders_comparison_with_confidence() -> None:
    html = render_report(_PROJECT, [], [_comparison()], [], [])
    assert "Cisco Meraki" in html
    assert "conf-confirmed" in html
    assert "conf-estimated" in html
    assert "Both vendors use subscription licensing." in html


def test_report_renders_advisor_markdown() -> None:
    messages = [
        Message(role="user", content="How do I justify this?"),
        Message(role="assistant", content="Frame it as a **5-year TCO**."),
    ]
    html = render_report(_PROJECT, [], [], [("CFO chat", messages)], [])
    assert "CFO chat" in html
    assert "<strong>5-year TCO</strong>" in html  # advisor markdown rendered


def test_report_surfaces_unresolved_artifacts() -> None:
    # PIS-20: a missing artifact is surfaced, not silently dropped.
    html = render_report(_PROJECT, [], [], [], ["TCO scenario abc123 (not found)"])
    assert "could not be included" in html
    assert "abc123" in html


def test_report_escapes_html_in_artifact_content() -> None:
    evil = TCOScenario(
        id="evil-1",
        scenario_name="<script>alert('x')</script>",
        inputs={},
        year_by_year=[],
        total_5yr=0.0,
        assumptions=[],
        warnings=[],
        lineage_id="evil-1",
        version=1,
        created_at=datetime(2026, 5, 25, tzinfo=UTC),
    )
    html = render_report(_PROJECT, [evil], [], [], [])
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


# ---------------------------------------------------------------------------
# PID amendment 1.5 — versioning surfaced in PDF + comparison artifact
# ---------------------------------------------------------------------------


def test_report_renders_tco_scenario_with_version_metadata() -> None:
    scenario = _tco(version=3)
    html = render_report(_PROJECT, [scenario], [], [], [])
    # The header surfaces the version label and save date.
    assert "v3" in html
    assert "2026-05-25" in html


def test_report_renders_tco_comparison_pair_with_delta() -> None:
    a = _tco(scenario_id="a", version=1, total=218_000)
    b = _tco(scenario_id="b", version=3, total=248_000)

    html = render_report(_PROJECT, [], [], [], [], [(a, b)])

    assert "TCO Comparison" in html
    assert "$218,000" in html
    assert "$248,000" in html
    # Delta should appear with a + sign because B exceeds A by $30,000.
    assert "$30,000" in html
    assert "+" in html


def test_report_render_report_back_compat_without_tco_comparisons() -> None:
    """Older call sites that omit `tco_comparisons` must still work."""
    html = render_report(_PROJECT, [], [], [], [])
    assert html.startswith("<!DOCTYPE html>")
