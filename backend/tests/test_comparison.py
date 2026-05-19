"""Unit tests for the Comparison Agent (PIS-11, PIS-20; Eval 3 / Eval 5).

The Anthropic client is mocked — no API calls, deterministic in CI. Evals 3
and 5 are manual review per PIS-09, but the matrix-completeness and
`unavailable`-fill behaviour they depend on is tested here.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.comparison import run_comparison_agent
from app.schemas.project import ProjectContext

_CTX = ProjectContext(
    name="Campus Wi-Fi Refresh",
    company="Acme Corp",
    description="200-AP refresh.",
    existing_infra="Legacy APs.",
    budget_ceiling=None,
)
_VENDORS = ["Cisco Meraki", "Juniper Mist"]
_CRITERIA = ["licensing model", "per-AP annual cost"]

_FULL = (
    '{"cells": ['
    '{"vendor": "Cisco Meraki", "criterion": "licensing model", '
    '"value": "Subscription", "source": "https://meraki.com", '
    '"confidence": "confirmed"}, '
    '{"vendor": "Cisco Meraki", "criterion": "per-AP annual cost", '
    '"value": "$150", "source": "https://cdw.com", "confidence": "estimated"}, '
    '{"vendor": "Juniper Mist", "criterion": "licensing model", '
    '"value": "Subscription", "source": "https://juniper.net", '
    '"confidence": "confirmed"}, '
    '{"vendor": "Juniper Mist", "criterion": "per-AP annual cost", '
    '"value": "$120", "source": "https://juniper.net", "confidence": "confirmed"}'
    '], "summary": "Both use subscription licensing; Mist is cheaper per AP."}'
)


def _response(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _mock_client(*, response: object | None = None, error: Exception | None = None):
    client = MagicMock()
    if error is not None:
        client.messages.create = AsyncMock(side_effect=error)
    else:
        client.messages.create = AsyncMock(return_value=response)
    return client


def _every_cell_present(result) -> bool:
    return all(
        criterion in result.matrix.get(vendor, {})
        for vendor in _VENDORS
        for criterion in _CRITERIA
    )


async def test_comparison_builds_full_matrix() -> None:
    # Eval 3: every criterion populated for both vendors, no empty cells.
    client = _mock_client(response=_response(_FULL))
    with patch("app.agents.comparison.get_anthropic_client", return_value=client):
        result = await run_comparison_agent(_VENDORS, _CRITERIA, [], _CTX)

    assert result.vendors == _VENDORS
    assert _every_cell_present(result)
    assert result.matrix["Juniper Mist"]["per-AP annual cost"].confidence == "confirmed"
    assert "subscription" in result.summary.lower()


async def test_comparison_fills_missing_cells_as_unavailable() -> None:
    # Eval 3 / Eval 5: cells the model omits are filled `unavailable`, never blank.
    partial = (
        '{"cells": [{"vendor": "Cisco Meraki", "criterion": "licensing model", '
        '"value": "Subscription", "source": "x", "confidence": "confirmed"}], '
        '"summary": "Partial data."}'
    )
    client = _mock_client(response=_response(partial))
    with patch("app.agents.comparison.get_anthropic_client", return_value=client):
        result = await run_comparison_agent(_VENDORS, _CRITERIA, [], _CTX)

    assert _every_cell_present(result)
    missing = result.matrix["Juniper Mist"]["per-AP annual cost"]
    assert missing.confidence == "unavailable"
    assert missing.source == ""


async def test_comparison_malformed_json_yields_unavailable_matrix() -> None:
    # PIS-20: unparseable output degrades to a full `unavailable` matrix.
    client = _mock_client(response=_response("sorry, could not compare"))
    with patch("app.agents.comparison.get_anthropic_client", return_value=client):
        result = await run_comparison_agent(_VENDORS, _CRITERIA, [], _CTX)

    assert _every_cell_present(result)
    assert all(
        result.matrix[v][c].confidence == "unavailable"
        for v in _VENDORS
        for c in _CRITERIA
    )


async def test_comparison_api_error_yields_unavailable_matrix() -> None:
    # PIS-20: an API failure must not crash the route.
    client = _mock_client(error=RuntimeError("API down"))
    with patch("app.agents.comparison.get_anthropic_client", return_value=client):
        result = await run_comparison_agent(_VENDORS, _CRITERIA, [], _CTX)

    assert _every_cell_present(result)
    assert all(
        result.matrix[v][c].confidence == "unavailable"
        for v in _VENDORS
        for c in _CRITERIA
    )


async def test_comparison_discards_cell_with_invalid_confidence() -> None:
    # Eval 5: an unverified value is never shown as confirmed; a bad
    # confidence value makes the cell fall back to `unavailable`.
    bad = (
        '{"cells": [{"vendor": "Cisco Meraki", "criterion": "licensing model", '
        '"value": "Subscription", "source": "", "confidence": "super-sure"}], '
        '"summary": "s"}'
    )
    client = _mock_client(response=_response(bad))
    with patch("app.agents.comparison.get_anthropic_client", return_value=client):
        result = await run_comparison_agent(_VENDORS, _CRITERIA, [], _CTX)

    assert result.matrix["Cisco Meraki"]["licensing model"].confidence == "unavailable"
