"""Anthropic API client factory.

Provides a process-wide async client. The API key is read through the
fail-fast accessor (SEC-12, AI-3) — it is never baked into a module constant
or a system prompt.
"""

from __future__ import annotations

from functools import lru_cache

from anthropic import AsyncAnthropic

from app.config import get_settings


@lru_cache
def get_anthropic_client() -> AsyncAnthropic:
    """Return the shared async Anthropic client.

    Raises ``ValueError`` (via ``require_anthropic_api_key``) when
    ``ANTHROPIC_API_KEY`` is unset, so a missing key fails loud at first use
    rather than producing a confusing downstream error.
    """
    return AsyncAnthropic(api_key=get_settings().require_anthropic_api_key())
