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

from app.agents import advisor, comparison
from app.schemas.project import ProjectContext
from app.schemas.research import ResearchResult


class _StopDetails:
    category = "cyber"
    explanation = "blocked by content classifier"


class _RefusalResponse:
    """Stand-in for an Anthropic Message that was refused."""

    stop_reason = "refusal"
    stop_details = _StopDetails()
    content: list = []


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
    monkeypatch.setattr(comparison, "get_anthropic_client", lambda: _FakeClient())

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


async def test_advisor_agent_handles_refusal(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(advisor, "get_anthropic_client", lambda: _FakeStreamClient())

    chunks: list[str] = []
    with caplog.at_level(logging.WARNING):
        async for chunk in advisor.stream_advisor_turn(
            history=[{"role": "user", "content": "Compare firewall vendors"}],
            project_context=_project(),
        ):
            chunks.append(chunk)

    output = "".join(chunks)
    # The user sees the intentional refusal message, not a silent empty turn.
    assert advisor._REFUSAL_MESSAGE in output
    assert "stop_reason=refusal" in caplog.text
    assert "cyber" in caplog.text
