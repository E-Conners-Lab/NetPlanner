"""Unit tests for the Research Agent (PIS-11, PIS-14, PIS-18, PIS-20, PIS-27).

The Anthropic client is mocked — these tests make no API calls, so they run
free and deterministically in CI.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.research import research
from app.schemas.research import ResearchResult


def _response(text: str) -> SimpleNamespace:
    """Build a fake Anthropic response carrying a single text block."""
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


def _mock_client(*, response: object | None = None, error: Exception | None = None):
    """Build a mock Anthropic client whose messages.create returns/raises."""
    client = MagicMock()
    if error is not None:
        client.messages.create = AsyncMock(side_effect=error)
    else:
        client.messages.create = AsyncMock(return_value=response)
    return client


_VALID_JSON = (
    '{"results": [{"vendor": "Cisco", "product": "Catalyst 9120", '
    '"price_point": "$795", "unit": "per AP", '
    '"source_url": "https://cisco.com/pricing", "confidence": "confirmed"}]}'
)


async def test_research_parses_valid_json() -> None:
    client = _mock_client(response=_response(_VALID_JSON))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("Cisco Catalyst 9120 pricing")

    assert isinstance(result, ResearchResult)
    assert result.query == "Cisco Catalyst 9120 pricing"
    assert len(result.results) == 1
    assert result.results[0].vendor == "Cisco"
    assert result.results[0].confidence == "confirmed"


async def test_research_strips_markdown_fences() -> None:
    fenced = f"```json\n{_VALID_JSON}\n```"
    client = _mock_client(response=_response(fenced))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("Cisco pricing")

    assert len(result.results) == 1


async def test_research_caps_results_at_three() -> None:
    # PIS-14: never more than 3 results per query.
    item = (
        '{"vendor": "V", "product": "P", "price_point": "$1", '
        '"unit": "u", "source_url": "", "confidence": "estimated"}'
    )
    five = '{"results": [' + ", ".join([item] * 5) + "]}"
    client = _mock_client(response=_response(five))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("anything")

    assert len(result.results) == 3


async def test_research_malformed_json_returns_empty() -> None:
    # PIS-20: unparseable output degrades to an empty result set, not a crash.
    client = _mock_client(response=_response("sorry, I could not find pricing"))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("obscure vendor")

    assert result.results == []
    assert result.query == "obscure vendor"


async def test_research_api_error_returns_empty() -> None:
    # PIS-20: an API failure must not crash the calling agent.
    client = _mock_client(error=RuntimeError("API down"))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("Juniper MIST pricing")

    assert result.results == []


async def test_research_skips_malformed_item_keeps_valid() -> None:
    mixed = (
        '{"results": ['
        '{"vendor": "Good", "product": "P", "price_point": "$1", '
        '"unit": "u", "source_url": "", "confidence": "estimated"}, '
        '{"vendor": "Bad — missing required fields"}'
        "]}"
    )
    client = _mock_client(response=_response(mixed))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("mixed quality")

    assert len(result.results) == 1
    assert result.results[0].vendor == "Good"


async def test_research_invalid_json_syntax_returns_empty() -> None:
    # Braces present but the content is not valid JSON — degrade gracefully.
    client = _mock_client(response=_response('{"results": [oops not json}'))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("broken json")

    assert result.results == []


async def test_research_non_list_results_returns_empty() -> None:
    # A "results" value that is not a list must not crash parsing.
    client = _mock_client(response=_response('{"results": "not a list"}'))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("wrong shape")

    assert result.results == []


async def test_research_missing_confidence_defaults_to_unavailable() -> None:
    # PIS-18: a missing confidence is never assumed — it defaults to unavailable.
    no_conf = (
        '{"results": [{"vendor": "V", "product": "P", '
        '"price_point": "", "unit": "u", "source_url": ""}]}'
    )
    client = _mock_client(response=_response(no_conf))
    with patch("app.agents.research.get_anthropic_client", return_value=client):
        result = await research("no confidence field")

    assert result.results[0].confidence == "unavailable"
