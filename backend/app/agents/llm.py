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

import logging
import re
from dataclasses import dataclass

import litellm

from app.agents.client import get_anthropic_client
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

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
