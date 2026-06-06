"""Unit tests for the provider-agnostic LLM wrapper (Phase 1 multi-provider).

The wrapper routes agent calls to either the native Anthropic SDK (default,
production path) or NVIDIA NIM via LiteLLM (eval only). Both providers are
mocked — no network calls, deterministic in CI.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents import llm
from app.config import Settings


def _settings(**overrides: object) -> SimpleNamespace:
    """A stand-in Settings with the attributes the wrapper reads."""
    base = {
        "provider": "anthropic",
        "comparison_model": "claude-sonnet-4-6",
        "advisor_model": "claude-sonnet-4-6",
        "nvidia_model": "nvidia/nemotron-3-super-120b-a12b",
        "nvidia_api_key": "nvapi-test",
    }
    base.update(overrides)
    settings = SimpleNamespace(**base)
    settings.require_nvidia_api_key = lambda: base["nvidia_api_key"]  # type: ignore[attr-defined]
    return settings


def _anthropic_response(text: str, *, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        stop_reason=stop_reason,
        stop_details=SimpleNamespace(category="cyber", explanation="blocked"),
    )


# --- model resolution ---------------------------------------------------------


def test_resolve_model_anthropic_uses_role_model() -> None:
    assert llm._resolve_model(_settings(), "comparison") == "claude-sonnet-4-6"


def test_resolve_model_nvidia_uses_nvidia_model() -> None:
    s = _settings(provider="nvidia_nim")
    assert llm._resolve_model(s, "comparison") == "nvidia/nemotron-3-super-120b-a12b"


# --- thinking strip (Finding #1: Nemotron emits chain-of-thought) -------------


def test_strip_thinking_removes_think_block() -> None:
    raw = '<think>The user wants JSON. Let me reason...</think>\n{"cells": []}'
    assert llm._strip_thinking(raw) == '{"cells": []}'


def test_strip_thinking_handles_thinking_tag_and_no_tags() -> None:
    assert llm._strip_thinking("<thinking>hmm</thinking>answer") == "answer"
    assert llm._strip_thinking("plain text") == "plain text"


# --- Anthropic path (default, production) -------------------------------------


async def test_complete_anthropic_returns_text() -> None:
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=_anthropic_response("hello"))
    with (
        patch.object(llm, "get_settings", return_value=_settings()),
        patch.object(llm, "get_anthropic_client", return_value=client),
    ):
        result = await llm.complete(
            role="comparison", system="sys", user="hi", max_tokens=128
        )
    assert result.text == "hello"
    assert result.refused is False
    # Anthropic-specific effort param is passed through (production parity).
    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-sonnet-4-6"
    assert kwargs["output_config"] == {"effort": "medium"}


async def test_complete_anthropic_flags_and_logs_refusal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = MagicMock()
    client.messages.create = AsyncMock(
        return_value=_anthropic_response("blocked", stop_reason="refusal")
    )
    with (
        patch.object(llm, "get_settings", return_value=_settings()),
        patch.object(llm, "get_anthropic_client", return_value=client),
        caplog.at_level(logging.WARNING),
    ):
        result = await llm.complete(
            role="comparison", system="sys", user="hi", max_tokens=128
        )
    assert result.refused is True
    assert result.refusal_category == "cyber"
    assert "stop_reason=refusal" in caplog.text
    assert "cyber" in caplog.text


# --- NVIDIA NIM path (eval only, via LiteLLM) ---------------------------------


async def test_complete_nvidia_routes_through_litellm_and_strips_thinking() -> None:
    nvidia_resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content='<think>reason</think>{"ok": 1}')
            )
        ]
    )
    acompletion = AsyncMock(return_value=nvidia_resp)
    with (
        patch.object(
            llm, "get_settings", return_value=_settings(provider="nvidia_nim")
        ),
        patch.object(llm.litellm, "acompletion", acompletion),
    ):
        result = await llm.complete(
            role="comparison", system="sys", user="hi", max_tokens=128
        )
    assert result.text == '{"ok": 1}'
    assert result.refused is False
    _, kwargs = acompletion.call_args
    # LiteLLM provider-prefixed model id, scoped key passed explicitly, and
    # drop_params set so Anthropic-only params never reach NIM.
    assert kwargs["model"] == "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
    assert kwargs["api_key"] == "nvapi-test"
    assert kwargs["drop_params"] is True
    # System instruction precedes user content (AI-1 ordering).
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["messages"][1] == {"role": "user", "content": "hi"}


async def test_complete_nvidia_missing_key_fails_loud() -> None:
    s = _settings(provider="nvidia_nim", nvidia_api_key="")

    def _raise() -> str:
        raise ValueError("NVIDIA_API_KEY is required when provider=nvidia_nim.")

    s.require_nvidia_api_key = _raise  # type: ignore[attr-defined]
    with patch.object(llm, "get_settings", return_value=s):
        with pytest.raises(ValueError, match="NVIDIA_API_KEY is required"):
            await llm.complete(
                role="comparison", system="sys", user="hi", max_tokens=128
            )


# --- config accessor ----------------------------------------------------------


def test_require_nvidia_api_key_raises_when_unset() -> None:
    with pytest.raises(ValueError, match="NVIDIA_API_KEY is required"):
        Settings(nvidia_api_key="").require_nvidia_api_key()


def test_require_nvidia_api_key_returns_value() -> None:
    assert Settings(nvidia_api_key="nvapi-abc").require_nvidia_api_key() == "nvapi-abc"


# --- tool schema translation --------------------------------------------------

_NEUTRAL_TOOL = {
    "name": "research",
    "description": "Search pricing.",
    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
}


def test_to_anthropic_tools_uses_input_schema() -> None:
    (tool,) = llm._to_anthropic_tools([_NEUTRAL_TOOL])
    assert tool["input_schema"] == _NEUTRAL_TOOL["parameters"]
    assert "parameters" not in tool


def test_to_openai_tools_wraps_function() -> None:
    (tool,) = llm._to_openai_tools([_NEUTRAL_TOOL])
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "research"
    assert tool["function"]["parameters"] == _NEUTRAL_TOOL["parameters"]


# --- format_tool_results (provider-native threading) --------------------------


def test_format_tool_results_anthropic_single_user_message() -> None:
    call = llm.ToolCall(id="toolu_1", name="research", arguments={})
    with patch.object(llm, "get_settings", return_value=_settings()):
        msgs = llm.format_tool_results([(call, "result text")])
    assert len(msgs) == 1
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"][0]["type"] == "tool_result"
    assert msgs[0]["content"][0]["tool_use_id"] == "toolu_1"


def test_format_tool_results_openai_one_tool_message_per_call() -> None:
    c1 = llm.ToolCall(id="call_1", name="research", arguments={})
    c2 = llm.ToolCall(id="call_2", name="research", arguments={})
    with patch.object(
        llm, "get_settings", return_value=_settings(provider="nvidia_nim")
    ):
        msgs = llm.format_tool_results([(c1, "a"), (c2, "b")])
    assert [m["role"] for m in msgs] == ["tool", "tool"]
    assert [m["tool_call_id"] for m in msgs] == ["call_1", "call_2"]


# --- NVIDIA streamed tool turn (the Advisor on NIM) ---------------------------


def _openai_chunk(
    *,
    content: str | None = None,
    tool_call: object | None = None,
    finish: str | None = None,
) -> SimpleNamespace:
    delta = SimpleNamespace(
        content=content, tool_calls=[tool_call] if tool_call else None
    )
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta, finish_reason=finish)])


def _tc_fragment(index: int, *, id: str = "", name: str = "", args: str = ""):
    return SimpleNamespace(
        index=index,
        id=id,
        function=SimpleNamespace(name=name or None, arguments=args or None),
    )


class _FakeOpenAIStream:
    def __init__(self, chunks: list) -> None:
        self._chunks = chunks

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._chunks:
            yield chunk


async def test_nvidia_tool_turn_streams_text_and_parses_tool_call() -> None:
    chunks = [
        _openai_chunk(content="Let me check. "),
        _openai_chunk(tool_call=_tc_fragment(0, id="call_1", name="research")),
        _openai_chunk(tool_call=_tc_fragment(0, args='{"query":')),
        _openai_chunk(
            tool_call=_tc_fragment(0, args='"AP price"}'), finish="tool_calls"
        ),
    ]
    acompletion = AsyncMock(return_value=_FakeOpenAIStream(chunks))
    with (
        patch.object(
            llm, "get_settings", return_value=_settings(provider="nvidia_nim")
        ),
        patch.object(llm.litellm, "acompletion", acompletion),
    ):
        async with llm.stream_tool_turn(
            role="advisor",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_NEUTRAL_TOOL],
            max_tokens=128,
        ) as turn:
            text = "".join([chunk async for chunk in turn])
            result = await turn.result()

    assert text == "Let me check. "
    assert result.stop == "tool_use"
    assert result.tool_calls == [
        llm.ToolCall(id="call_1", name="research", arguments={"query": "AP price"})
    ]
    # Provider-native assistant message carries the OpenAI tool_calls shape.
    assert result.assistant_message["tool_calls"][0]["function"]["name"] == "research"
    # OpenAI request shape: system folded into messages, openai-format tools.
    _, kwargs = acompletion.call_args
    assert kwargs["messages"][0] == {"role": "system", "content": "sys"}
    assert kwargs["tools"][0]["type"] == "function"
    assert kwargs["stream"] is True
    assert kwargs["drop_params"] is True


async def test_nvidia_tool_turn_content_filter_is_refusal() -> None:
    chunks = [_openai_chunk(content="partial", finish="content_filter")]
    acompletion = AsyncMock(return_value=_FakeOpenAIStream(chunks))
    with (
        patch.object(
            llm, "get_settings", return_value=_settings(provider="nvidia_nim")
        ),
        patch.object(llm.litellm, "acompletion", acompletion),
    ):
        async with llm.stream_tool_turn(
            role="advisor",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_NEUTRAL_TOOL],
            max_tokens=128,
        ) as turn:
            _ = "".join([chunk async for chunk in turn])
            result = await turn.result()

    assert result.stop == "refusal"


async def test_nvidia_tool_turn_plain_text_ends() -> None:
    chunks = [_openai_chunk(content="Just advice."), _openai_chunk(finish="stop")]
    acompletion = AsyncMock(return_value=_FakeOpenAIStream(chunks))
    with (
        patch.object(
            llm, "get_settings", return_value=_settings(provider="nvidia_nim")
        ),
        patch.object(llm.litellm, "acompletion", acompletion),
    ):
        async with llm.stream_tool_turn(
            role="advisor",
            system="sys",
            messages=[{"role": "user", "content": "hi"}],
            tools=[_NEUTRAL_TOOL],
            max_tokens=128,
        ) as turn:
            text = "".join([chunk async for chunk in turn])
            result = await turn.result()

    assert text == "Just advice."
    assert result.stop == "end"
    assert result.tool_calls == []
