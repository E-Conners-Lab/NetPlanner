"""Application settings, loaded from environment / .env (SEC-12, SEC-13).

Secrets (ANTHROPIC_API_KEY) are read from the environment only — never hardcoded
and never committed. See `.env.example` for the expected variables.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins as a clean list, splitting the comma-separated value."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]

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


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance."""
    return Settings()
