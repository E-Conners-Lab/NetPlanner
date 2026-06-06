"""Agents handle a model safety refusal (`stop_reason: "refusal"`) cleanly.

When the Anthropic API blocks the output (the safety classifier — commonly the
`cyber` classifier reacting to security-adjacent terms pulled in via
web_search), the response carries `stop_reason: "refusal"` and `stop_details`.
The Advisor and Comparison agents must surface a clear message and log the
reason rather than streaming raw refusal text or silently returning empties.
"""

from __future__ import annotations

import logging

import pytest
from httpx import AsyncClient

from app.agents import advisor, comparison
from app.schemas.project import ProjectContext
from app.schemas.research import ResearchResult


class _StopDetails:
    category = "cyber"
    explanation = "blocked by content classifier"


class _TextBlock:
    """A stand-in content block carrying the provider's raw blocked text."""

    type = "text"
    text = "Output blocked by content filter"


class _RefusalResponse:
    """Stand-in for an Anthropic Message that was refused."""

    stop_reason = "refusal"
    stop_details = _StopDetails()
    content: list = [_TextBlock()]


# --- Comparison agent (single non-streaming call) -----------------------------


class _FakeMessages:
    async def create(self, **_kwargs: object) -> _RefusalResponse:
        return _RefusalResponse()


class _FakeClient:
    messages = _FakeMessages()


def _project() -> ProjectContext:
    return ProjectContext(
        name="DC Fabric",
        company="Meridian Health",
        description="Spine-leaf upgrade",
        existing_infra="Nexus 7000",
        budget_ceiling=1_000_000,
    )


async def test_comparison_agent_handles_refusal(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # The Comparison agent now routes through the provider-agnostic wrapper; the
    # refusal originates in the wrapper's native Anthropic path (default
    # provider), so patch the client the wrapper uses.
    monkeypatch.setattr("app.agents.llm.get_anthropic_client", lambda: _FakeClient())

    with caplog.at_level(logging.WARNING):
        result = await comparison.run_comparison_agent(
            vendors=["Arista", "Cisco"],
            criteria=["price per port", "power draw"],
            research_data=[ResearchResult(query="arista pricing", results=[])],
            project_context=_project(),
        )

    # The matrix is fully populated with `unavailable` so the UI still renders.
    assert set(result.matrix) == {"Arista", "Cisco"}
    for vendor in result.matrix.values():
        for cell in vendor.values():
            assert cell.confidence == "unavailable"
    # The summary is the honest refusal explanation, not a parsed/empty one.
    assert result.summary == comparison._REFUSAL_SUMMARY
    # The structured stop details were logged for the operator.
    assert "stop_reason=refusal" in caplog.text
    assert "cyber" in caplog.text


# --- Advisor agent (streaming) ------------------------------------------------


class _FakeStream:
    def __init__(self, final: _RefusalResponse) -> None:
        self._final = final

    async def __aenter__(self) -> _FakeStream:
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    def __aiter__(self) -> _FakeStream:
        return self

    async def __anext__(self) -> object:
        raise StopAsyncIteration

    async def get_final_message(self) -> _RefusalResponse:
        return self._final


class _FakeStreamMessages:
    def stream(self, **_kwargs: object) -> _FakeStream:
        return _FakeStream(_RefusalResponse())


class _FakeStreamClient:
    messages = _FakeStreamMessages()


async def test_advisor_agent_raises_refusal_and_logs_raw(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A refusal raises AdvisorRefusalError (the route turns it into a clean notice)
    and logs the structured details + raw blocked text server-side."""
    # The Advisor now streams through the provider-agnostic wrapper; the refusal
    # surfaces from the wrapper's native Anthropic path, so patch its client.
    monkeypatch.setattr(
        "app.agents.llm.get_anthropic_client", lambda: _FakeStreamClient()
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(advisor.AdvisorRefusalError):
            async for _chunk in advisor.stream_advisor_turn(
                history=[{"role": "user", "content": "Compare firewall vendors"}],
                project_context=_project(),
            ):
                pass

    # The structured stop details and the raw blocked text are captured for the
    # operator — but only in the server log, never returned to the caller.
    assert "stop_reason=refusal" in caplog.text
    assert "cyber" in caplog.text
    assert "Output blocked by content filter" in caplog.text


async def test_advisor_route_replaces_blocked_output(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """On a refusal the SSE stream emits a `replace` event with the clean
    notice, so the raw provider block text never becomes the final answer."""

    async def _refusing_turn(history, context, summary=None):  # type: ignore[no-untyped-def]
        yield "Output blocked by content filter"  # raw provider text (streamed)
        raise advisor.AdvisorRefusalError

    monkeypatch.setattr("app.routes.advisor.stream_advisor_turn", _refusing_turn)

    project = (
        await client.post(
            "/api/projects",
            json={"name": "Refusal", "description": "220 APs across 3 buildings."},
        )
    ).json()

    resp = await client.post(
        f"/api/projects/{project['id']}/advisor",
        json={"message": "Compare firewall vendors"},
    )

    assert resp.status_code == 200
    body = resp.text
    # The clean notice is delivered as a replace event that overwrites the bubble.
    # (SSE JSON-escapes non-ASCII, so match a distinctive ASCII fragment.)
    assert '"type": "replace"' in body
    assert "safety classifier" in body
    assert "Rephrasing or re-running" in body
