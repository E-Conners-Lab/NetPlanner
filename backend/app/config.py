"""Application settings, loaded from environment / .env (SEC-12, SEC-13).

Secrets (ANTHROPIC_API_KEY) are read from the environment only — never hardcoded
and never committed. See `.env.example` for the expected variables.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Supported LLM providers. ``anthropic`` is the production default; ``nvidia_nim``
# routes through LiteLLM to the NVIDIA API catalog for the multi-provider eval.
Provider = Literal["anthropic", "nvidia_nim"]


class Settings(BaseSettings):
    """Typed application configuration.

    Values resolve from (in order) real environment variables, then a local
    `.env` file. Unknown keys are ignored so the same file can serve tooling.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Runtime -----------------------------------------------------------
    environment: str = "development"

    # --- Persistence -------------------------------------------------------
    # SQLite lives in ./data/ (gitignored). Async driver: aiosqlite.
    database_url: str = "sqlite+aiosqlite:///./data/netplanner.db"

    # --- Secrets (SEC-12) --------------------------------------------------
    # Empty by default; the AI layer (Phase 2+) fails loud if it is missing.
    anthropic_api_key: str = ""

    # --- LLM provider (multi-provider eval) --------------------------------
    # ``anthropic`` (default) keeps the native Anthropic path untouched.
    # ``nvidia_nim`` routes agents through LiteLLM to the NVIDIA API catalog
    # for evaluation only — never the production default. Scoped, dev-only key
    # (SEC-13/15); fails loud via ``require_nvidia_api_key`` when selected.
    provider: Provider = "anthropic"
    nvidia_api_key: str = ""
    # Catalog model id used for all NVIDIA-routed agents during the eval.
    # Override per-run (e.g. to the comparator) via NVIDIA_MODEL in .env.
    nvidia_model: str = "nvidia/nemotron-3-super-120b-a12b"
    # Phase 2b LLM-as-judge model (NeMo-rubric fallback). A strong third-family
    # model on NVIDIA's catalog, distinct from every model under test to avoid
    # self-preference bias (SPEC §5). Verified live in Phase 0; override via
    # NVIDIA_JUDGE_MODEL (never hardcode a catalog id in logic — they change).
    nvidia_judge_model: str = "qwen/qwen3.5-122b-a10b"

    # --- Authentication (SEC-01 / SEC-14 / SEC-16) -------------------------
    # JWT signing secret. Empty in dev means a generated per-process key —
    # production fails loud at startup if the value is unset or the default.
    jwt_secret: str = ""
    # Cookie name + max-age (seconds). 8 hours is a sensible session length
    # for an advisory tool; the cookie is also rotated on login (SEC-04).
    session_cookie_name: str = "netplanner_session"
    session_max_age_seconds: int = 8 * 60 * 60
    # Double-submit CSRF cookie (SEC-07). Readable by the SPA (not httpOnly)
    # so it can be echoed back in the X-CSRF-Token header; verified against
    # the cookie with a constant-time comparison on every mutating request.
    csrf_cookie_name: str = "netplanner_csrf"
    csrf_header_name: str = "X-CSRF-Token"
    # Set to False in non-HTTPS development to allow the cookie to be sent.
    # Production keeps the default (Secure flag enabled).
    session_cookie_secure: bool = True
    # Force HSTS on every response. Production sends HSTS automatically
    # (keyed off ``environment``); this flag additionally enables it for a
    # non-production HTTPS deployment. Off by default so plain-HTTP dev does
    # not pin the local origin to HTTPS.
    enable_hsts: bool = False

    # --- CORS (SEC-08 family) ---------------------------------------------
    # Comma-separated list. Dev default is the Vite dev server origin.
    cors_origins: str = "http://localhost:5173"

    # --- Model assignments (PID Domain 7 / PIS-29) ------------------------
    # Contract values; override per-environment via .env. The Sonnet-tier
    # model was updated to claude-sonnet-4-6 in PID amendment 1.1. Research
    # moved from Haiku to Sonnet in amendment 1.4 (quality over marginal cost).
    advisor_model: str = "claude-sonnet-4-6"
    tco_model: str = "claude-sonnet-4-6"
    comparison_model: str = "claude-sonnet-4-6"
    report_model: str = "claude-sonnet-4-6"
    research_model: str = "claude-sonnet-4-6"

    # --- Advisor tool-use budget (eval Finding #6) -------------------------
    # How many research rounds the Advisor may run before a forced,
    # tools-disabled synthesis turn. Tool-use propensity is model-dependent —
    # Nemotron loops the research tool where Claude answers directly — so the
    # budget is per-provider. Anthropic/Claude keeps the original 4 rounds;
    # NVIDIA is capped tighter. Override via *_MAX_TOOL_ROUNDS in .env.
    advisor_max_tool_rounds: int = 4
    nvidia_max_tool_rounds: int = 2

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a clean list, splitting the comma-separated value."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

    def advisor_tool_rounds(self) -> int:
        """Research-round budget for the active provider (eval Finding #6).

        Dispatches on ``provider`` so a model with a heavier tool-use
        propensity (Nemotron) is capped tighter than the baseline (Claude),
        rather than sharing one global constant.
        """
        if self.provider == "nvidia_nim":
            return self.nvidia_max_tool_rounds
        return self.advisor_max_tool_rounds

    def require_anthropic_api_key(self) -> str:
        """Return the Anthropic API key, failing loud if it is unset (SEC-12).

        Phase 0 makes no API calls, so the key may legitimately be empty. The
        AI layer (Phase 2+) must call this accessor rather than reading the
        attribute directly, so a missing key fails fast with a clear error
        instead of producing a confusing downstream failure.
        """
        if not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required for the AI layer. "
                "Set it in your environment or .env file."
            )
        return self.anthropic_api_key

    def require_nvidia_api_key(self) -> str:
        """Return the NVIDIA API key, failing loud if it is unset (SEC-12).

        Only called when ``provider == "nvidia_nim"``. The scoped, dev-only
        catalog key (SEC-13/15) must be set explicitly — a missing key fails
        fast here rather than producing a confusing LiteLLM auth error.
        """
        if not self.nvidia_api_key:
            raise ValueError(
                "NVIDIA_API_KEY is required when provider=nvidia_nim. "
                "Set it in your environment or .env file."
            )
        return self.nvidia_api_key

    def require_jwt_secret(self) -> str:
        """Return the JWT signing secret (SEC-12 / SEC-14).

        Production requires the operator to supply a strong, persistent value
        — otherwise every restart invalidates sessions and admin tokens.
        Development falls back to a generated key so the app boots locally
        with no `.env`, but never in production.
        """
        if self.jwt_secret:
            return self.jwt_secret
        if self.environment == "production":
            raise ValueError(
                "JWT_SECRET is required in production. "
                "Set a strong random value in your environment or .env file."
            )
        # Dev / test default: a stable per-process random key. Tests that need
        # a deterministic secret override `jwt_secret` directly.
        import secrets

        self.jwt_secret = secrets.token_urlsafe(32)
        return self.jwt_secret


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance."""
    return Settings()
