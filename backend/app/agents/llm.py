"""Provider-agnostic LLM access (Phase 1 — multi-provider eval).

NetPlanner's agents call ``complete()`` instead of an SDK directly, so the same
agent code runs against either provider:

- ``anthropic`` (default, production): the native Anthropic SDK, unchanged —
  including the ``effort`` extended-thinking control and ``stop_reason:
  "refusal"`` safety semantics.
- ``nvidia_nim`` (eval only): the NVIDIA API catalog via LiteLLM's OpenAI-
  compatible ``nvidia_nim/`` provider. This is selected by the ``provider``
  setting and never the production default.

The wrapper normalizes both providers to :class:`LLMResult`, hiding the three
Anthropic-vs-OpenAI coupling points (tool/message shape, stop reasons, and the
reasoning chain-of-thought that NIM models emit) from the agents.

AI-3: API keys are read through fail-fast settings accessors at call time, never
baked into a module constant or a system prompt.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal

import litellm

from app.agents.client import get_anthropic_client
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# A neutral tool spec the agents pass in; translated per provider below.
# Shape: {"name": str, "description": str, "parameters": <JSON schema dict>}.
NeutralTool = dict[str, object]

# Reasoning models (e.g. Nemotron) wrap their chain-of-thought in <think> /
# <thinking> tags (Phase 0 Finding #1). Strip it so downstream JSON parsing
# sees only the answer.
_THINKING_RE = re.compile(
    r"<think(?:ing)?>.*?</think(?:ing)?>", re.DOTALL | re.IGNORECASE
)


@dataclass(frozen=True)
class LLMResult:
    """A normalized, provider-agnostic completion result.

    ``refused`` is Anthropic-specific (safety classifier ``stop_reason:
    "refusal"``); NIM has no equivalent, so it is always ``False`` there.
    """

    text: str
    refused: bool = False
    refusal_category: str | None = None
    refusal_explanation: str | None = None


def _resolve_model(settings: Settings, role: str) -> str:
    """Return the catalog model id for ``role`` under the active provider.

    Anthropic uses the per-role contract models (``<role>_model``); NVIDIA uses
    the single ``nvidia_model`` for every role during the eval.
    """
    if settings.provider == "nvidia_nim":
        return settings.nvidia_model
    return getattr(settings, f"{role}_model")


def _strip_thinking(text: str) -> str:
    """Remove reasoning chain-of-thought blocks from a model's text output."""
    return _THINKING_RE.sub("", text).strip()


def _text_of(response: object) -> str:
    """Join the text content blocks of an Anthropic message."""
    return "".join(
        block.text
        for block in getattr(response, "content", [])
        if getattr(block, "type", None) == "text"
    )


async def _complete_anthropic(
    settings: Settings, role: str, system: str, user: str, max_tokens: int, effort: str
) -> LLMResult:
    """Native Anthropic path — preserves the production behavior exactly."""
    client = get_anthropic_client()
    response = await client.messages.create(  # type: ignore[call-overload]
        model=_resolve_model(settings, role),
        max_tokens=max_tokens,
        system=system,
        output_config={"effort": effort},
        messages=[{"role": "user", "content": user}],
    )
    if getattr(response, "stop_reason", None) == "refusal":
        details = getattr(response, "stop_details", None)
        category = getattr(details, "category", None)
        explanation = getattr(details, "explanation", None)
        logger.warning(
            "Model refused (stop_reason=refusal): category=%s explanation=%s",
            category,
            explanation,
        )
        return LLMResult(
            text=_text_of(response),
            refused=True,
            refusal_category=category,
            refusal_explanation=explanation,
        )
    return LLMResult(text=_text_of(response))


async def _complete_nvidia(
    settings: Settings, role: str, system: str, user: str, max_tokens: int
) -> LLMResult:
    """NVIDIA NIM path via LiteLLM (OpenAI-compatible ``nvidia_nim/`` provider).

    ``drop_params`` discards Anthropic-only params NIM does not understand;
    ``temperature=0`` keeps eval runs reproducible. Reasoning chain-of-thought
    is stripped so the agent's JSON parser sees only the answer.
    """
    api_key = settings.require_nvidia_api_key()
    response = await litellm.acompletion(
        model=f"nvidia_nim/{_resolve_model(settings, role)}",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0,
        api_key=api_key,
        drop_params=True,
    )
    content = response.choices[0].message.content or ""
    return LLMResult(text=_strip_thinking(content))


async def complete(
    *, role: str, system: str, user: str, max_tokens: int, effort: str = "medium"
) -> LLMResult:
    """Run a single non-streaming completion against the active provider.

    Args:
        role: Agent role (e.g. ``"comparison"``) used to resolve the model id.
        system: System instruction — always placed before user content (AI-1).
        user: The user/prompt content (untrusted; the agent marks boundaries).
        max_tokens: Output cap. Reasoning models need headroom (Finding #1).
        effort: Anthropic extended-thinking effort; ignored by NIM.

    Returns:
        A provider-agnostic :class:`LLMResult`.
    """
    settings = get_settings()
    if settings.provider == "nvidia_nim":
        return await _complete_nvidia(settings, role, system, user, max_tokens)
    return await _complete_anthropic(settings, role, system, user, max_tokens, effort)


# --- Streaming with tools (the conversational Advisor) ------------------------
#
# The Advisor streams text and may invoke tools across several rounds. The two
# providers disagree on every detail — tool schema, stream event shape, the
# assistant/tool message format, and stop reasons — so the wrapper normalizes
# all of it to a provider-agnostic :class:`ToolCall` / :class:`TurnResult`, plus
# ``format_tool_results`` for threading tool output back into the conversation.


@dataclass(frozen=True)
class ToolCall:
    """A normalized tool invocation requested by the model."""

    id: str
    name: str
    arguments: dict


@dataclass
class TurnResult:
    """The outcome of one streamed turn, after its text has been consumed.

    ``assistant_message`` is the provider-native message to append to the
    conversation before the tool results — opaque to the agent.
    """

    stop: Literal["end", "tool_use", "refusal"]
    tool_calls: list[ToolCall] = field(default_factory=list)
    assistant_message: dict | None = None
    refusal_category: str | None = None
    refusal_explanation: str | None = None
    refusal_text: str = ""


def _to_anthropic_tools(tools: list[NeutralTool]) -> list[dict]:
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["parameters"],
        }
        for t in tools
    ]


def _to_openai_tools(tools: list[NeutralTool]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools
    ]


class _AnthropicToolTurn:
    """Wrap the native Anthropic streaming context manager (production path)."""

    def __init__(
        self,
        client: object,
        *,
        model: str,
        system: str,
        messages: list,
        tools: list[dict],
        max_tokens: int,
        effort: str,
        allow_tools: bool = True,
    ) -> None:
        # ``.stream()`` only builds the context manager (no I/O); the request
        # happens in __aenter__. Anthropic keeps `system` and `thinking` as
        # top-level params and disables thinking for the low-latency chat turn.
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system,
            "tools": tools,
            "thinking": {"type": "disabled"},
            "output_config": {"effort": effort},
            "messages": messages,
        }
        # The graceful-cap synthesis turn forbids tool use so the model must
        # answer from the research already gathered (Advisor Finding #6). When
        # tools are allowed we omit `tool_choice` entirely — the production path
        # is byte-for-byte unchanged.
        if not allow_tools:
            kwargs["tool_choice"] = {"type": "none"}
        self._cm = client.messages.stream(**kwargs)  # type: ignore[attr-defined]
        self._stream: object | None = None

    async def __aenter__(self) -> _AnthropicToolTurn:
        self._stream = await self._cm.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> object:
        return await self._cm.__aexit__(*exc)

    def __aiter__(self) -> AsyncIterator[str]:
        return self._text_chunks()

    async def _text_chunks(self) -> AsyncIterator[str]:
        async for event in self._stream:  # type: ignore[union-attr]
            if event.type == "content_block_delta" and event.delta.type == "text_delta":
                yield event.delta.text

    async def result(self) -> TurnResult:
        final = await self._stream.get_final_message()  # type: ignore[union-attr]
        stop_reason = getattr(final, "stop_reason", None)
        if stop_reason == "refusal":
            details = getattr(final, "stop_details", None)
            return TurnResult(
                stop="refusal",
                refusal_category=getattr(details, "category", None),
                refusal_explanation=getattr(details, "explanation", None),
                refusal_text=_text_of(final),
            )
        if stop_reason == "tool_use":
            blocks = [
                b
                for b in getattr(final, "content", [])
                if getattr(b, "type", "") == "tool_use"
            ]
            calls = [
                ToolCall(
                    id=b.id,
                    name=b.name,
                    arguments=b.input if isinstance(b.input, dict) else {},
                )
                for b in blocks
            ]
            return TurnResult(
                stop="tool_use",
                tool_calls=calls,
                assistant_message={"role": "assistant", "content": final.content},
            )
        return TurnResult(stop="end")


class _OpenAIToolTurn:
    """Stream tool calls through LiteLLM's OpenAI-compatible interface (NIM)."""

    def __init__(
        self,
        *,
        model: str,
        system: str,
        messages: list,
        tools: list[dict],
        max_tokens: int,
        api_key: str,
        allow_tools: bool = True,
    ) -> None:
        # ``tool_choice="none"`` forces the graceful-cap synthesis turn to answer
        # without calling tools (Advisor Finding #6); ``"auto"`` is the normal
        # path, unchanged.
        self._kwargs = {
            "model": model,
            "messages": [{"role": "system", "content": system}, *messages],
            "tools": tools,
            "tool_choice": "auto" if allow_tools else "none",
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": 0,
            "api_key": api_key,
            "drop_params": True,
        }
        self._stream: object | None = None
        self._text: list[str] = []
        # Streamed tool-call fragments, accumulated by their position index.
        self._fragments: dict[int, dict[str, str]] = {}
        self._finish: str | None = None

    async def __aenter__(self) -> _OpenAIToolTurn:
        self._stream = await litellm.acompletion(**self._kwargs)
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    def __aiter__(self) -> AsyncIterator[str]:
        return self._text_chunks()

    async def _text_chunks(self) -> AsyncIterator[str]:
        async for chunk in self._stream:  # type: ignore[union-attr]
            choice = chunk.choices[0]
            if choice.finish_reason:
                self._finish = choice.finish_reason
            delta = choice.delta
            for frag in getattr(delta, "tool_calls", None) or []:
                acc = self._fragments.setdefault(
                    frag.index, {"id": "", "name": "", "args": ""}
                )
                if frag.id:
                    acc["id"] = frag.id
                fn = getattr(frag, "function", None)
                if fn and getattr(fn, "name", None):
                    acc["name"] = fn.name
                if fn and getattr(fn, "arguments", None):
                    acc["args"] += fn.arguments
            # Yield only answer content, not reasoning_content — reasoning models
            # stream chain-of-thought separately (Finding #1); we never surface it.
            content = getattr(delta, "content", None)
            if content:
                self._text.append(content)
                yield content

    async def result(self) -> TurnResult:
        if self._fragments and self._finish == "tool_calls":
            calls: list[ToolCall] = []
            native: list[dict] = []
            for index in sorted(self._fragments):
                frag = self._fragments[index]
                try:
                    args = json.loads(frag["args"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                calls.append(ToolCall(id=frag["id"], name=frag["name"], arguments=args))
                native.append(
                    {
                        "id": frag["id"],
                        "type": "function",
                        "function": {
                            "name": frag["name"],
                            "arguments": frag["args"] or "{}",
                        },
                    }
                )
            return TurnResult(
                stop="tool_use",
                tool_calls=calls,
                assistant_message={
                    "role": "assistant",
                    "content": "".join(self._text) or None,
                    "tool_calls": native,
                },
            )
        if self._finish == "content_filter":
            return TurnResult(stop="refusal", refusal_text="".join(self._text))
        return TurnResult(stop="end")


def stream_tool_turn(
    *,
    role: str,
    system: str,
    messages: list,
    tools: list[NeutralTool],
    max_tokens: int,
    effort: str = "low",
    allow_tools: bool = True,
) -> _AnthropicToolTurn | _OpenAIToolTurn:
    """Open a streamed, tool-capable turn against the active provider.

    Use as ``async with stream_tool_turn(...) as turn``: iterate ``turn`` for
    text chunks, then ``await turn.result()`` (inside the context) for the
    normalized :class:`TurnResult`.

    Set ``allow_tools=False`` to forbid tool use for this turn (normalized to
    Anthropic ``tool_choice={"type": "none"}`` / OpenAI ``tool_choice="none"``)
    — used for the Advisor's graceful-cap synthesis turn (Finding #6).
    """
    settings = get_settings()
    if settings.provider == "nvidia_nim":
        return _OpenAIToolTurn(
            model=f"nvidia_nim/{_resolve_model(settings, role)}",
            system=system,
            messages=messages,
            tools=_to_openai_tools(tools),
            max_tokens=max_tokens,
            api_key=settings.require_nvidia_api_key(),
            allow_tools=allow_tools,
        )
    return _AnthropicToolTurn(
        get_anthropic_client(),
        model=_resolve_model(settings, role),
        system=system,
        messages=messages,
        tools=_to_anthropic_tools(tools),
        max_tokens=max_tokens,
        effort=effort,
        allow_tools=allow_tools,
    )


def format_tool_results(results: list[tuple[ToolCall, str]]) -> list[dict]:
    """Build provider-native tool-result messages to append to the conversation.

    Anthropic expects one ``user`` message carrying ``tool_result`` blocks;
    OpenAI/NIM expects one ``tool`` message per call.
    """
    if get_settings().provider == "nvidia_nim":
        return [
            {"role": "tool", "tool_call_id": call.id, "content": output}
            for call, output in results
        ]
    return [
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": call.id, "content": output}
                for call, output in results
            ],
        }
    ]
