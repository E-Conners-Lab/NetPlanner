# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Authoritative documents

- `docs/PID.md` — the **build contract** (Project Initiation Document). Capabilities, exclusions, eval cases, agent decomposition, and rules like PIS-17 (anchor block on every Advisor turn), PIS-24 (hard guardrails), PIS-27 (pricing confidence policy). Read before changing any agent or schema.
- `docs/RUNBOOK.md` — reproducible setup, the quality gate, and the phase-by-phase build journal (append a journal entry on non-trivial changes; append a troubleshooting entry on non-trivial errors).
- `README.md` — capability list and quick start.

## Common commands

Backend (run from `backend/`, managed by [uv](https://docs.astral.sh/uv/) — `uv.lock` is the committed source of truth):

```bash
uv sync                                              # install locked deps (use --frozen in CI)
uv run alembic upgrade head                          # apply migrations
uv run uvicorn app.main:app --reload                 # dev server on :8000

uv run ruff check app tests alembic                  # lint
uv run black --check app tests alembic               # format check
uv run isort --check-only app tests alembic          # import order
uv run mypy app --ignore-missing-imports             # types
uv run bandit -r app alembic -ll                     # security static analysis
uv run alembic check                                  # ORM ↔ migrations parity
uv run pytest                                        # tests
uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=80   # CI form
uv run pytest tests/test_advisor.py::test_name       # single test
```

Frontend (run from `frontend/`):

```bash
npm install
npm run dev        # Vite dev server on :5173
npm run lint       # ESLint
npm run build      # production build
```

Full stack via Docker (after `cp .env.example .env` and adding `ANTHROPIC_API_KEY`):

```bash
docker compose up
```

Tooling config for ruff/black/isort lives in the **root** `pyproject.toml`; ESLint config is `frontend/eslint.config.js`. Pytest config (asyncio mode auto, `pythonpath=.`) lives in `backend/pyproject.toml`.

## Architecture

### Backend (`backend/app/`)

FastAPI + async SQLAlchemy on SQLite (`aiosqlite`). Alembic owns schema changes; `app/database.py:init_db` does a forgiving first-run `create_all` from the lifespan handler.

Five layers, each in its own subpackage:

- **`routes/`** — FastAPI routers, one per feature (`projects`, `advisor`, `tco`, `comparison`, `reports`). Registered under `/api` in `app/main.py`. They depend on `get_db` (per-request `AsyncSession`).
- **`services/`** — domain logic that orchestrates ORM models and agent calls. Routes are thin; the work lives here.
- **`agents/`** — Anthropic-powered agents. **All agents pass through `agents/client.py:get_anthropic_client`**, which uses `get_settings().require_anthropic_api_key()` to fail loud if the key is unset (SEC-12, AI-3). Per-agent model assignments come from `config.py` (`advisor_model`, `tco_model`, `comparison_model`, `report_model`, `research_model` — all `claude-sonnet-4-6` since PID amendment 1.4). The **Advisor is the only multi-turn agent** and calls **Research** as a tool (server-side `web_search`); follow the prompt-injection defenses in their module docstrings (system anchor first, explicit boundary markers, every result re-validated against the Pydantic schema).
- **`schemas/`** — Pydantic v2 models. The agent **handoff contracts** (e.g. `ProjectContext`, `ResearchResult`) live here; downstream agents depend on these, never directly on ORM models.
- **`models/`** — SQLAlchemy ORM. Every model inherits `Base` + `TimestampMixin` from `app/database.py`; primary keys are UUID4 strings via `new_uuid()`.

`SecurityHeadersMiddleware` (X-Frame-Options, Referrer-Policy, HSTS, X-Content-Type-Options) is applied globally; the CSP for the SPA lives in `frontend/nginx.conf`, not in Python. CORS origins come from the `CORS_ORIGINS` env var. In production (`environment == "production"`) `/docs`, `/redoc`, and `/openapi.json` are disabled.

### Frontend (`frontend/src/`)

React 18 + Vite + React Router v6 + Tailwind + Recharts. SPA shell in `App.jsx` is a sidebar + topbar wrapping route outlets:

```
/                              Dashboard
/projects/:id                  ProjectDetail
/projects/:id/{advisor|tco|comparison|reports}
```

`api/client.js` is a shared Axios instance; `VITE_API_URL` (default `/api`) lets it work with both the Vite dev proxy and the Nginx `proxy_pass` in the production image. Custom hooks in `src/hooks/` (`useApi`, `useProject`, `useProjects`, `useStream`) wrap API calls; `useStream` handles the Advisor SSE streaming response.

### Cross-cutting conventions

- **Advisory only.** Every output is a recommendation for human review (PID Domain 1, PIS-04). Reports carry the mandatory disclaimer (PIS-24 #4).
- **Pricing confidence tagging** (PIS-27): `confirmed` requires a specific URL or named publication; "vendor docs"/bare vendor names downgrade to `estimated`. Missing data is never assumed — use `unavailable` and surface it in the UI.
- **Secrets posture.** `ANTHROPIC_API_KEY` is read only via `Settings.require_anthropic_api_key()`. Phase 0/1 code paths may run with an empty key; the AI layer fails fast at first use.
- **Eval gate (PIS-10).** 6 of 7 PID evals must pass; eval 4 (no assumed financial inputs) and eval 5 (no unverified pricing as confirmed) are zero-tolerance. Re-run the relevant tests before merging changes that touch the TCO or pricing paths.
- **TCO versioning** (PID amendment 1.5): `TCOScenario.lineage_id` is a grouping key, **not** an FK — deletes don't cascade through the lineage. A new save with `parent_scenario_id` inherits the parent's lineage and bumps `version`; without it, a fresh lineage starts at v1 anchored to its own id. The whole feature is additive — old saves and old payloads still round-trip unchanged.

## CI quality gate

`.github/workflows/ci.yml` runs three jobs on every PR to `main`:

1. **Backend gate** (hard): ruff, black, isort, mypy, bandit, `alembic upgrade head && alembic check`, `pytest --cov-fail-under=80`. Native deps for WeasyPrint (`libpango`, `libpangocairo`, `libgdk-pixbuf`) are installed before `uv sync --frozen`.
2. **Frontend gate** (hard): ESLint + production Vite build.
3. **Security scans** (informational — `continue-on-error: true`): `pip-audit`, `npm audit`, Semgrep, TruffleHog. Remove the `continue-on-error` to make these block merges (SEC-29 / SEC-35).
