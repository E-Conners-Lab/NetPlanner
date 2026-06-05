"""Re-downloaded reports return the original PDF snapshot (audit-integrity)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_TCO_BODY = {
    "scenario_name": "AP refresh",
    "inputs": {
        "device_count": 200,
        "hardware_cost_per_unit": 600,
        "licensing_cost_per_unit_year": 98,
    },
}


async def _make_tco(client: AsyncClient, project_id: str) -> str:
    resp = await client.post(f"/api/projects/{project_id}/tco", json=_TCO_BODY)
    return resp.json()["id"]


async def test_redownload_returns_original_pdf_bytes(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The PDF returned on re-download is the snapshot stored at create time."""
    counter = {"n": 0}

    async def _fake_pdf(html: str) -> bytes:
        # Distinct payload per call so a fresh render is detectable.
        counter["n"] += 1
        return f"%PDF-call-{counter['n']}".encode()

    monkeypatch.setattr("app.routes.reports.pdf.generate_pdf", _fake_pdf)

    project = (await client.post("/api/projects", json={"name": "Snap"})).json()
    tco_id = await _make_tco(client, project["id"])

    create = await client.post(
        f"/api/projects/{project['id']}/reports",
        json={"title": "Q1", "artifacts": [{"kind": "tco", "ref_id": tco_id}]},
    )
    assert create.status_code == 200
    original_bytes = create.content

    listing = await client.get(f"/api/projects/{project['id']}/reports")
    report_id = listing.json()[0]["id"]

    # Even after deleting the TCO scenario the original snapshot survives.
    re_download = await client.get(
        f"/api/projects/{project['id']}/reports/{report_id}/pdf"
    )
    assert re_download.status_code == 200
    assert re_download.content == original_bytes
    # The render function was not called again on re-download (snapshot served).
    assert counter["n"] == 1


async def test_redownload_uses_user_submitted_title_in_filename(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_pdf(html: str) -> bytes:
        return b"%PDF-fake"

    monkeypatch.setattr("app.routes.reports.pdf.generate_pdf", _fake_pdf)

    project = (await client.post("/api/projects", json={"name": "Naming"})).json()
    tco_id = await _make_tco(client, project["id"])
    await client.post(
        f"/api/projects/{project['id']}/reports",
        json={
            "title": "Riverbend Capex Plan",
            "artifacts": [{"kind": "tco", "ref_id": tco_id}],
        },
    )
    listing = await client.get(f"/api/projects/{project['id']}/reports")
    report_id = listing.json()[0]["id"]

    resp = await client.get(f"/api/projects/{project['id']}/reports/{report_id}/pdf")
    assert "riverbend-capex-plan" in resp.headers["content-disposition"].lower()


async def test_user_submitted_title_appears_in_pdf_header_html(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The Report Agent emits the user-submitted title in the PDF header."""
    captured: dict[str, str] = {}

    async def _capture_pdf(html: str) -> bytes:
        captured["html"] = html
        return b"%PDF-fake"

    monkeypatch.setattr("app.routes.reports.pdf.generate_pdf", _capture_pdf)

    project = (await client.post("/api/projects", json={"name": "Hdr"})).json()
    tco_id = await _make_tco(client, project["id"])
    await client.post(
        f"/api/projects/{project['id']}/reports",
        json={
            "title": "Custom Header Title",
            "artifacts": [{"kind": "tco", "ref_id": tco_id}],
        },
    )

    assert "Custom Header Title" in captured["html"]
    # The legacy fallback prefix is no longer used.
    assert "NetPlanner Report — Hdr" not in captured["html"]
