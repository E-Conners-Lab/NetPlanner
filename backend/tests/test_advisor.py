"""Unit tests for the Advisor Agent (PIS-11, PIS-13, PIS-16, PIS-17, PIS-20).

The Anthropic streaming client is mocked — no API calls, deterministic in CI.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.advisor import (
    AdvisorRefusalError,
    _build_system,
    _select_recent,
    project_context_is_sufficient,
    stream_advisor_turn,
)
from app.schemas.project import ProjectContext
from app.schemas.research import ResearchItem, ResearchResult

_CTX = ProjectContext(
    name="Campus Wi-Fi Refresh",
    company="Acme Corp",
    description="Replace 200 aging access points.",
    existing_infra="200 legacy 802.11ac APs on a Cisco WLC.",
    budget_ceiling=400000.0,
)


def _delta(text: str) -> SimpleNamespace:
    """A text_delta stream event."""
    return SimpleNamespace(
        type="content_block_delta",
        delta=SimpleNamespace(type="text_delta", text=text),
    )


class _FakeStream:
    """Mimics the Anthropic async streaming context manager."""

    def __init__(self, events: list, final: SimpleNamespace) -> None:
        self._events = events
        self._final = final

    async def __aenter__(self) -> _FakeStream:
        return self

    async def __aexit__(self, *_exc: object) -> bool:
        return False

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for event in self._events:
            yield event

    async def get_final_message(self) -> SimpleNamespace:
        return self._final


async def _collect(history: list[dict], context: ProjectContext) -> str:
    return "".join([chunk async for chunk in stream_advisor_turn(history, context)])


def _tool_use_stream(text: str = "Looking that up. ") -> _FakeStream:
    """A stream that ends by requesting the `research` tool."""
    tool_block = SimpleNamespace(
        type="tool_use", id="toolu_x", name="research", input={"query": "AP pricing"}
    )
    return _FakeStream(
        [_delta(text)],
        SimpleNamespace(stop_reason="tool_use", content=[tool_block]),
    )


def _settings_stub(rounds: int) -> SimpleNamespace:
    """Stand-in for get_settings() exposing the per-provider round budget."""
    return SimpleNamespace(advisor_tool_rounds=lambda: rounds)


_RESEARCH = ResearchResult(
    query="AP pricing",
    results=[
        ResearchItem(
            vendor="Juniper",
            product="AP45",
            price_point="$130",
            unit="per AP",
            source_url="https://example.test",
            confidence="estimated",
        )
    ],
)


# --- Streaming -------------------------------------------------------------


async def test_advisor_streams_text() -> None:
    stream = _FakeStream(
        [_delta("Frame it as "), _delta("a 5-year TCO.")],
        SimpleNamespace(stop_reason="end_turn", content=[]),
    )
    client = MagicMock()
    client.messages.stream = MagicMock(return_value=stream)

    with patch("app.agents.llm.get_anthropic_client", return_value=client):
        text = await _collect([{"role": "user", "content": "Justify MIST"}], _CTX)

    assert text == "Frame it as a 5-year TCO."


async def test_advisor_invokes_research_tool() -> None:
    # PIS-13: the Advisor calls Research as a tool, then continues.
    tool_block = SimpleNamespace(
        type="tool_use", id="toolu_1", name="research", input={"query": "AP pricing"}
    )
    stream1 = _FakeStream(
        [_delta("Let me check pricing. ")],
        SimpleNamespace(stop_reason="tool_use", content=[tool_block]),
    )
    stream2 = _FakeStream(
        [_delta("Cisco APs run about $800 each.")],
        SimpleNamespace(stop_reason="end_turn", content=[]),
    )
    client = MagicMock()
    client.messages.stream = MagicMock(side_effect=[stream1, stream2])

    research_result = ResearchResult(
        query="AP pricing",
        results=[
            ResearchItem(
                vendor="Cisco",
                product="Catalyst 9120",
                price_point="$800",
                unit="per AP",
                source_url="https://cisco.com",
                confidence="confirmed",
            )
        ],
    )

    with (
        patch("app.agents.llm.get_anthropic_client", return_value=client),
        patch(
            "app.agents.advisor.research", AsyncMock(return_value=research_result)
        ) as mock_research,
    ):
        text = await _collect([{"role": "user", "content": "How much?"}], _CTX)

    mock_research.assert_awaited_once()
    assert "Cisco APs run about $800 each." in text


async def test_advisor_error_yields_graceful_message() -> None:
    # PIS-20: a failure surfaces a generic message, never an unhandled crash.
    client = MagicMock()
    client.messages.stream = MagicMock(side_effect=RuntimeError("API down"))

    with patch("app.agents.llm.get_anthropic_client", return_value=client):
        text = await _collect([{"role": "user", "content": "hi"}], _CTX)

    assert "error occurred" in text.lower()


# --- Graceful cap (Finding #6): exhausting the budget yields a real answer ---


async def test_advisor_graceful_cap_synthesizes_answer_without_tools() -> None:
    # Budget = 1 round. The model loops the tool that round, then the forced
    # no-tools turn MUST synthesize a real answer from the research gathered —
    # never the old dead-end "(Research budget reached)" notice.
    synthesis = _FakeStream(
        [_delta("Based on the research, AP45 at $130 is the better value.")],
        SimpleNamespace(stop_reason="end_turn", content=[]),
    )
    client = MagicMock()
    client.messages.stream = MagicMock(side_effect=[_tool_use_stream(), synthesis])

    with (
        patch("app.agents.llm.get_anthropic_client", return_value=client),
        patch("app.agents.advisor.get_settings", return_value=_settings_stub(1)),
        patch("app.agents.advisor.research", AsyncMock(return_value=_RESEARCH)),
    ):
        text = await _collect([{"role": "user", "content": "Which AP?"}], _CTX)

    assert "the better value" in text
    assert "budget reached" not in text.lower()
    # Two model turns: one tool round, then the forced synthesis turn.
    assert client.messages.stream.call_count == 2
    # The final (synthesis) turn disabled tools so the model had to answer.
    _, last_kwargs = client.messages.stream.call_args_list[-1]
    assert last_kwargs["tool_choice"] == {"type": "none"}


async def test_advisor_respects_round_budget_before_forcing_synthesis() -> None:
    # Budget = 2 rounds: research runs exactly twice, then one no-tools turn.
    synthesis = _FakeStream(
        [_delta("Synthesized answer.")],
        SimpleNamespace(stop_reason="end_turn", content=[]),
    )
    client = MagicMock()
    client.messages.stream = MagicMock(
        side_effect=[_tool_use_stream(), _tool_use_stream(), synthesis]
    )
    mock_research = AsyncMock(return_value=_RESEARCH)

    with (
        patch("app.agents.llm.get_anthropic_client", return_value=client),
        patch("app.agents.advisor.get_settings", return_value=_settings_stub(2)),
        patch("app.agents.advisor.research", mock_research),
    ):
        text = await _collect([{"role": "user", "content": "Which AP?"}], _CTX)

    assert mock_research.await_count == 2
    assert client.messages.stream.call_count == 3
    assert "Synthesized answer." in text
    assert "budget reached" not in text.lower()


async def test_advisor_refusal_on_forced_synthesis_raises() -> None:
    # If the forced synthesis turn is blocked by the safety classifier, the
    # Advisor still surfaces the clean refusal path — not a dead-end notice.
    refusal = _FakeStream(
        [],
        SimpleNamespace(
            stop_reason="refusal",
            stop_details=SimpleNamespace(category="cyber", explanation="blocked"),
            content=[],
        ),
    )
    client = MagicMock()
    client.messages.stream = MagicMock(side_effect=[_tool_use_stream(), refusal])

    with (
        patch("app.agents.llm.get_anthropic_client", return_value=client),
        patch("app.agents.advisor.get_settings", return_value=_settings_stub(1)),
        patch("app.agents.advisor.research", AsyncMock(return_value=_RESEARCH)),
        pytest.raises(AdvisorRefusalError),
    ):
        await _collect([{"role": "user", "content": "Which AP?"}], _CTX)


# --- Helpers ---------------------------------------------------------------


def test_project_context_sufficient_and_insufficient() -> None:
    assert project_context_is_sufficient(_CTX) is True
    empty = ProjectContext(
        name="Bare", company="", description="", existing_infra="", budget_ceiling=None
    )
    assert project_context_is_sufficient(empty) is False
    # Whitespace-only context is still insufficient.
    blank = ProjectContext(
        name="Bare",
        company="",
        description="   ",
        existing_infra="\n",
        budget_ceiling=None,
    )
    assert project_context_is_sufficient(blank) is False


def test_build_system_includes_anchor_guardrails_and_context() -> None:
    system = _build_system(_CTX)
    assert "NetPlanner's business advisor" in system  # PIS-17 anchor
    assert "Never provide network device configuration" in system  # PIS-24
    assert "Campus Wi-Fi Refresh" in system  # project context
    assert "<<PROJECT_CONTEXT>>" in system


def test_select_recent_caps_history_at_20() -> None:
    # PIS-16: history is capped at the most recent 20 messages.
    history = [{"role": "user", "content": str(i)} for i in range(30)]
    recent = _select_recent(history)
    assert len(recent) == 20
    assert recent[0]["content"] == "10"
    assert recent[-1]["content"] == "29"
