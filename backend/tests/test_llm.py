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
