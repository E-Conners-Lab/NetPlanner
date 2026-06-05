"""Automated eval / route tests for FastAPI routes (PID Domain 2, PIS-09).

Eval 4 — edge case: incomplete TCO input must not generate a model (Phase 3).
Eval 7 — edge case: vague advisor input must request project context first.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Message
from app.schemas.comparison import ComparisonCell, ComparisonResult
from app.schemas.research import ResearchResult


async def test_eval4_incomplete_tco_input_is_rejected(client: AsyncClient) -> None:
    """PID Eval 4 — incomplete input edge case.

    Input: TCO form submitted with a device count but no hardware cost.

    Expected: the request is rejected (422) and NO scenario is created —
    financial inputs are never silently assumed (PIS-04, zero-tolerance
    PIS-10).
    """
    project = (await client.post("/api/projects", json={"name": "TCO Project"})).json()

    resp = await client.post(
        f"/api/projects/{project['id']}/tco",
        json={
            "scenario_name": "Incomplete",
            "inputs": {"device_count": 200, "licensing_cost_per_unit_year": 98},
        },
    )

    assert resp.status_code == 422  # hardware_cost_per_unit is required
    # Zero TCO output produced — nothing was persisted.
    listing = await client.get(f"/api/projects/{project['id']}/tco")
    assert listing.json() == []


_TCO_BODY = {
    "scenario_name": "AP Refresh",
    "inputs": {
        "device_count": 200,
        "hardware_cost_per_unit": 600,
        "licensing_cost_per_unit_year": 98,
    },
}


async def test_tco_preview_does_not_persist(client: AsyncClient) -> None:
    project = (await client.post("/api/projects", json={"name": "Campus"})).json()

    preview = await client.post(
        f"/api/projects/{project['id']}/tco/preview", json=_TCO_BODY
    )
    assert preview.status_code == 200
    assert preview.json()["total_5yr"] == 218_000

    # Preview computes but never saves.
    assert (await client.get(f"/api/projects/{project['id']}/tco")).json() == []


async def test_tco_save_then_list(client: AsyncClient) -> None:
    project = (await client.post("/api/projects", json={"name": "Campus"})).json()

    saved = await client.post(f"/api/projects/{project['id']}/tco", json=_TCO_BODY)
    assert saved.status_code == 201
    assert saved.json()["total_5yr"] == 218_000

    listing = await client.get(f"/api/projects/{project['id']}/tco")
    assert len(listing.json()) == 1
    assert listing.json()[0]["scenario_name"] == "AP Refresh"


async def test_tco_preview_surfaces_reasonableness_warning(
    client: AsyncClient,
) -> None:
    project = (await client.post("/api/projects", json={"name": "Anomalous"})).json()

    resp = await client.post(
        f"/api/projects/{project['id']}/tco/preview",
        json={
            "scenario_name": "Typo",
            "inputs": {
                "device_count": 200,
                "hardware_cost_per_unit": 6,
                "licensing_cost_per_unit_year": 98,
            },
        },
    )
    assert resp.status_code == 200
    assert resp.json()["warnings"]  # PIS-21 reasonableness flag


async def test_tco_on_missing_project_returns_404(client: AsyncClient) -> None:
    resp = await client.post("/api/projects/missing/tco/preview", json=_TCO_BODY)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PID amendment 1.5 — versioning + refresh events + lineage convenience route
# ---------------------------------------------------------------------------


async def test_tco_save_without_parent_starts_new_lineage(client: AsyncClient) -> None:
    project = (await client.post("/api/projects", json={"name": "Lineage"})).json()

    saved = await client.post(f"/api/projects/{project['id']}/tco", json=_TCO_BODY)
    body = saved.json()

    assert body["version"] == 1
    assert body["lineage_id"] == body["id"]


async def test_tco_save_with_parent_creates_next_version(client: AsyncClient) -> None:
    project = (await client.post("/api/projects", json={"name": "Versions"})).json()

    v1 = (
        await client.post(f"/api/projects/{project['id']}/tco", json=_TCO_BODY)
    ).json()
    v2_body = {**_TCO_BODY, "parent_scenario_id": v1["id"]}
    v2 = (await client.post(f"/api/projects/{project['id']}/tco", json=v2_body)).json()

    assert v2["lineage_id"] == v1["lineage_id"]
    assert v2["version"] == 2
    assert v2["id"] != v1["id"]


async def test_tco_save_with_parent_in_other_project_returns_404(
    client: AsyncClient,
) -> None:
    """Parent-scenario references must not cross project boundaries (SEC-27)."""
    project_a = (await client.post("/api/projects", json={"name": "A"})).json()
    project_b = (await client.post("/api/projects", json={"name": "B"})).json()
    v1_a = (
        await client.post(f"/api/projects/{project_a['id']}/tco", json=_TCO_BODY)
    ).json()

    cross = await client.post(
        f"/api/projects/{project_b['id']}/tco",
        json={**_TCO_BODY, "parent_scenario_id": v1_a["id"]},
    )
    assert cross.status_code == 404


async def test_tco_lineage_route_returns_full_version_history(
    client: AsyncClient,
) -> None:
    project = (await client.post("/api/projects", json={"name": "History"})).json()

    v1 = (
        await client.post(f"/api/projects/{project['id']}/tco", json=_TCO_BODY)
    ).json()
    (
        await client.post(
            f"/api/projects/{project['id']}/tco",
            json={**_TCO_BODY, "parent_scenario_id": v1["id"]},
        )
    ).json()

    history = (
        await client.get(
            f"/api/projects/{project['id']}/tco/lineages/{v1['lineage_id']}"
        )
    ).json()

    assert [row["version"] for row in history] == [1, 2]


async def test_tco_lineage_route_does_not_leak_across_projects(
    client: AsyncClient,
) -> None:
    project_a = (await client.post("/api/projects", json={"name": "A"})).json()
    project_b = (await client.post("/api/projects", json={"name": "B"})).json()
    v1_a = (
        await client.post(f"/api/projects/{project_a['id']}/tco", json=_TCO_BODY)
    ).json()

    cross = await client.get(
        f"/api/projects/{project_b['id']}/tco/lineages/{v1_a['lineage_id']}"
    )
    assert cross.status_code == 200
    assert cross.json() == []


async def test_tco_refresh_event_round_trips_through_save(client: AsyncClient) -> None:
    project = (await client.post("/api/projects", json={"name": "Refresh"})).json()

    body = {
        "scenario_name": "Phased refresh",
        "inputs": {
            **_TCO_BODY["inputs"],
            "refresh_events": [{"year": 3, "percent_of_devices": 25}],
        },
    }
    saved = (await client.post(f"/api/projects/{project['id']}/tco", json=body)).json()

    # The Year-3 refresh hardware figure round-trips through persistence.
    assert saved["year_by_year"][2]["refresh_hardware"] == 200 * 0.25 * 600
    # And shows up in the assumptions.
    assert any("Year 3 refresh" in line for line in saved["assumptions"])


async def test_comparison_generate_and_list(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Generating a comparison saves it and it appears in the list."""

    async def _fake_research(query: str) -> ResearchResult:
        return ResearchResult(query=query, results=[])

    async def _fake_agent(vendors, criteria, research_data, context):  # noqa: ANN001
        return ComparisonResult(
            vendors=vendors,
            criteria=criteria,
            matrix={
                v: {
                    c: ComparisonCell(value="x", source="", confidence="estimated")
                    for c in criteria
                }
                for v in vendors
            },
            summary="Test comparison.",
        )

    monkeypatch.setattr("app.routes.comparison.research", _fake_research)
    monkeypatch.setattr("app.routes.comparison.run_comparison_agent", _fake_agent)

    project = (await client.post("/api/projects", json={"name": "Cmp"})).json()
    body = {
        "vendors": ["Cisco Meraki", "Juniper Mist"],
        "criteria": ["licensing model"],
    }

    resp = await client.post(f"/api/projects/{project['id']}/comparison", json=body)
    assert resp.status_code == 201
    assert resp.json()["summary"] == "Test comparison."

    listing = await client.get(f"/api/projects/{project['id']}/comparison")
    assert len(listing.json()) == 1
    assert listing.json()[0]["vendors"] == ["Cisco Meraki", "Juniper Mist"]


async def test_comparison_rejects_fewer_than_two_vendors(client: AsyncClient) -> None:
    # PIS-02 #4: a comparison needs 2-3 platforms.
    project = (await client.post("/api/projects", json={"name": "Cmp"})).json()
    resp = await client.post(
        f"/api/projects/{project['id']}/comparison",
        json={"vendors": ["Only One"], "criteria": ["licensing model"]},
    )
    assert resp.status_code == 422


async def test_comparison_rejects_duplicate_vendors(client: AsyncClient) -> None:
    """Duplicate vendor names (case-insensitive) are rejected at the schema."""
    project = (await client.post("/api/projects", json={"name": "Cmp"})).json()
    resp = await client.post(
        f"/api/projects/{project['id']}/comparison",
        json={
            "vendors": ["Cisco Meraki", "cisco meraki"],
            "criteria": ["licensing model"],
        },
    )
    assert resp.status_code == 422
    assert "duplicate" in resp.text.lower()


async def test_comparison_rejects_vendor_containing_another(
    client: AsyncClient,
) -> None:
    """Paste-error guard: vendor A containing vendor B is rejected.

    Mirrors the bad row found during demo walkthrough where field-1 held
    two vendor names mashed together, producing a malformed list title.
    """
    project = (await client.post("/api/projects", json={"name": "Cmp"})).json()
    resp = await client.post(
        f"/api/projects/{project['id']}/comparison",
        json={
            "vendors": [
                "Cisco Catalyst 9300 Arista CCS-720XP",
                "Arista CCS-720XP",
            ],
            "criteria": ["licensing model"],
        },
    )
    assert resp.status_code == 422
    assert "paste error" in resp.text.lower()


async def test_comparison_rejects_criterion_containing_another(
    client: AsyncClient,
) -> None:
    """Paste-error guard: criterion A containing criterion B is rejected.

    Symmetric to the vendor case. A live Riverbend Health run shipped a
    comparison whose first criterion read "PricingCloud management depth
    and multi-site administration experience" — two intended criteria
    mashed together. The matrix rendered a confused row with all
    `unavailable` cells. Validate at the route boundary instead.
    """
    project = (await client.post("/api/projects", json={"name": "Cmp"})).json()
    resp = await client.post(
        f"/api/projects/{project['id']}/comparison",
        json={
            "vendors": ["Cisco Meraki", "Juniper Mist"],
            "criteria": [
                "PricingCloud management depth and multi-site administration",
                "Cloud management depth and multi-site administration",
            ],
        },
    )
    assert resp.status_code == 422
    assert "paste error" in resp.text.lower()


async def test_comparison_rejects_duplicate_criteria(
    client: AsyncClient,
) -> None:
    """Duplicate-criterion guard: case-insensitive duplicates are rejected.

    Symmetric to the duplicate-vendor case. Two identical criteria would
    produce a malformed matrix where the second column overwrites the
    first.
    """
    project = (await client.post("/api/projects", json={"name": "Cmp"})).json()
    resp = await client.post(
        f"/api/projects/{project['id']}/comparison",
        json={
            "vendors": ["Cisco Meraki", "Juniper Mist"],
            "criteria": ["licensing model", "Licensing Model"],
        },
    )
    assert resp.status_code == 422
    assert "duplicate" in resp.text.lower()


async def test_comparison_on_missing_project_returns_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/projects/missing/comparison",
        json={"vendors": ["A", "B"], "criteria": ["licensing model"]},
    )
    assert resp.status_code == 404


async def _save_tco(client: AsyncClient, project_id: str) -> str:
    """Save a TCO scenario and return its id (helper for report tests)."""
    resp = await client.post(
        f"/api/projects/{project_id}/tco",
        json={
            "scenario_name": "S",
            "inputs": {
                "device_count": 10,
                "hardware_cost_per_unit": 600,
                "licensing_cost_per_unit_year": 100,
            },
        },
    )
    return resp.json()["id"]


async def test_report_generates_downloadable_pdf(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report request returns a PDF download (WeasyPrint mocked)."""

    async def _fake_pdf(html: str) -> bytes:
        return b"%PDF-1.7 fake"

    monkeypatch.setattr("app.routes.reports.pdf.generate_pdf", _fake_pdf)

    project = (await client.post("/api/projects", json={"name": "Rpt"})).json()
    tco_id = await _save_tco(client, project["id"])

    resp = await client.post(
        f"/api/projects/{project['id']}/reports",
        json={
            "title": "Q1 Planning Report",
            "artifacts": [{"kind": "tco", "ref_id": tco_id}],
        },
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert "attachment" in resp.headers["content-disposition"]


async def test_report_lists_export_history(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_pdf(html: str) -> bytes:
        return b"%PDF-fake"

    monkeypatch.setattr("app.routes.reports.pdf.generate_pdf", _fake_pdf)

    project = (await client.post("/api/projects", json={"name": "Rpt"})).json()
    tco_id = await _save_tco(client, project["id"])
    await client.post(
        f"/api/projects/{project['id']}/reports",
        json={"title": "R1", "artifacts": [{"kind": "tco", "ref_id": tco_id}]},
    )

    listing = await client.get(f"/api/projects/{project['id']}/reports")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["title"] == "R1"


async def test_report_on_missing_project_returns_404(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/projects/missing/reports",
        json={"title": "R", "artifacts": [{"kind": "tco", "ref_id": "x"}]},
    )
    assert resp.status_code == 404


async def test_report_redownload_returns_pdf(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A previously-generated report can be re-downloaded by id."""

    async def _fake_pdf(html: str) -> bytes:
        return b"%PDF-1.7 fake"

    monkeypatch.setattr("app.routes.reports.pdf.generate_pdf", _fake_pdf)

    project = (await client.post("/api/projects", json={"name": "Rd"})).json()
    tco_id = await _save_tco(client, project["id"])
    create = await client.post(
        f"/api/projects/{project['id']}/reports",
        json={
            "title": "Re-download Test",
            "artifacts": [{"kind": "tco", "ref_id": tco_id}],
        },
    )
    assert create.status_code == 200
    report_id = (await client.get(f"/api/projects/{project['id']}/reports")).json()[0][
        "id"
    ]

    resp = await client.get(f"/api/projects/{project['id']}/reports/{report_id}/pdf")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")
    assert "attachment" in resp.headers["content-disposition"]
    # SEC-24: sensitive responses must not be cached.
    assert resp.headers["cache-control"] == "no-store"


async def test_report_redownload_missing_report_returns_404(
    client: AsyncClient,
) -> None:
    project = (await client.post("/api/projects", json={"name": "Rd"})).json()
    resp = await client.get(f"/api/projects/{project['id']}/reports/missing/pdf")
    assert resp.status_code == 404


async def test_list_conversation_messages_returns_history(
    client: AsyncClient, db_session: AsyncSession, auth_user: object
) -> None:
    """GET /conversations/:id/messages returns the chronological history."""
    from app.models.conversation import Conversation, Message
    from app.models.project import Project

    project = Project(name="Hist", owner_id=auth_user.id)  # type: ignore[attr-defined]
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    conv = Conversation(project_id=project.id, title="First chat")
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    db_session.add_all(
        [
            Message(conversation_id=conv.id, role="user", content="hi"),
            Message(conversation_id=conv.id, role="assistant", content="hello"),
        ]
    )
    await db_session.commit()

    resp = await client.get(
        f"/api/projects/{project.id}/conversations/{conv.id}/messages"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [m["role"] for m in body] == ["user", "assistant"]
    assert [m["content"] for m in body] == ["hi", "hello"]


async def test_list_conversation_messages_wrong_project_returns_404(
    client: AsyncClient, db_session: AsyncSession, auth_user: object
) -> None:
    """SEC-27 — a conversation in project A is not retrievable via project B."""
    from app.models.conversation import Conversation
    from app.models.project import Project

    project_a = Project(name="A", owner_id=auth_user.id)  # type: ignore[attr-defined]
    project_b = Project(name="B", owner_id=auth_user.id)  # type: ignore[attr-defined]
    db_session.add_all([project_a, project_b])
    await db_session.commit()
    await db_session.refresh(project_a)
    await db_session.refresh(project_b)

    conv = Conversation(project_id=project_a.id, title="A-only")
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)

    resp = await client.get(
        f"/api/projects/{project_b.id}/conversations/{conv.id}/messages"
    )
    assert resp.status_code == 404


async def test_report_redownload_wrong_project_returns_404(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-27 — a report belonging to project A is not retrievable via project B."""

    async def _fake_pdf(html: str) -> bytes:
        return b"%PDF-fake"

    monkeypatch.setattr("app.routes.reports.pdf.generate_pdf", _fake_pdf)

    project_a = (await client.post("/api/projects", json={"name": "A"})).json()
    project_b = (await client.post("/api/projects", json={"name": "B"})).json()
    tco_id = await _save_tco(client, project_a["id"])
    await client.post(
        f"/api/projects/{project_a['id']}/reports",
        json={"title": "Owned by A", "artifacts": [{"kind": "tco", "ref_id": tco_id}]},
    )
    report_id = (await client.get(f"/api/projects/{project_a['id']}/reports")).json()[
        0
    ]["id"]

    resp = await client.get(f"/api/projects/{project_b['id']}/reports/{report_id}/pdf")
    assert resp.status_code == 404


async def test_eval7_vague_advisor_input_requires_context(client: AsyncClient) -> None:
    """PID Eval 7 — vague advisor input edge case.

    Input: "what should I buy?" against a project with no context set.

    Expected: the system requests project context before answering — no
    generic vendor recommendation, and no model call is made.
    """
    project = (await client.post("/api/projects", json={"name": "Bare Project"})).json()

    resp = await client.post(
        f"/api/projects/{project['id']}/advisor",
        json={"message": "what should I buy?"},
    )

    assert resp.status_code == 200
    body = resp.text.lower()
    # The response asks for project context...
    assert "more about this project" in body
    # ...and does not name a vendor or give a recommendation.
    assert "cisco" not in body and "juniper" not in body


async def test_advisor_streams_response_and_persists(
    client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A project with context streams an answer and persists both messages."""

    async def _fake_turn(history: object, context: object, summary: str | None = None):
        yield "Frame it as "
        yield "a 5-year TCO."

    monkeypatch.setattr("app.routes.advisor.stream_advisor_turn", _fake_turn)

    project = (
        await client.post(
            "/api/projects",
            json={
                "name": "Campus Refresh",
                "description": "Replace 200 access points.",
                "existing_infra": "200 legacy APs on a Cisco WLC.",
            },
        )
    ).json()

    resp = await client.post(
        f"/api/projects/{project['id']}/advisor",
        json={"message": "How do I justify this to my CFO?"},
    )

    assert resp.status_code == 200
    body = resp.text
    # Both streamed tokens and a terminating done event are present.
    assert "Frame it as " in body
    assert "a 5-year TCO." in body
    assert '"type": "done"' in body

    # The user message and the assistant reply were both persisted (PIS-25).
    rows = (await db_session.execute(select(Message))).scalars().all()
    assert {m.role for m in rows} == {"user", "assistant"}
