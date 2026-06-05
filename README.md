# NetPlanner

[![CI](https://github.com/E-Conners-Lab/NetPlanner/actions/workflows/ci.yml/badge.svg)](https://github.com/E-Conners-Lab/NetPlanner/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18-61dafb.svg)](https://react.dev/)

**AI-powered business decision support for network engineers.**

NetPlanner helps network engineers build Total Cost of Ownership (TCO) models,
compare vendors, and generate stakeholder-ready PDF reports — without requiring
finance or business expertise. Every output is advisory: a recommendation for
human review, never an automated action.

The full contract for this build is in [`docs/PID.md`](docs/PID.md) — the
Project Initiation Document. Read it before changing anything.

For reproducible setup, the quality gate, and the phase-by-phase build journal
(including every issue hit and how it was fixed), see
[`docs/RUNBOOK.md`](docs/RUNBOOK.md).

---

## Capabilities (at launch)

- **Projects** — create, edit, and delete planning scenarios.
- **AI Advisor** — conversational, web-search-backed, streaming responses
  scoped to a project's context.
- **TCO Calculator** — structured inputs → year-by-year cost model → chart.
  Optional mid-cycle refresh events (e.g. swap 25% of APs in Year 3) and
  versioned snapshots so a revised scenario never overwrites the artifact you
  already shared with finance.
- **TCO Comparison** — pick any two saved scenarios (or two versions of one
  lineage) for a screen-side comparison with overlay chart, per-year delta
  table, and assumption diff. The same pair can be embedded in the PDF
  report as a `tco_comparison` artifact.
- **Vendor Comparison** — 2–3 platforms compared across your criteria, with
  live pricing research and `confirmed` / `estimated` / `unavailable`
  confidence indicators.
- **Reports** — export any combination of artifacts as a formatted PDF.
  The version picker shows which TCO scenarios are the latest revision in
  their lineage, and every TCO header in the PDF carries its `vN · saved
  YYYY-MM-DD` tag.

All pricing data carries a confidence tag, and every PDF carries a disclaimer:
estimates are for planning only — verify with vendors before budget submission.

---

## Screenshots

A visual walkthrough of the Dashboard, AI Advisor, TCO Calculator, and Vendor
Comparison is in
[`docs/netplanner-screenshot-carousel.html`](docs/netplanner-screenshot-carousel.html)
— open it in a browser. To embed static captures inline here, drop them into
`docs/images/` and reference them in this section.

---

## Tech Stack

| Layer        | Stack                                                            |
|--------------|------------------------------------------------------------------|
| Backend      | Python 3.12, FastAPI, SQLAlchemy (async) + SQLite, Alembic, Pydantic v2 |
| AI           | Anthropic Python SDK — Claude Sonnet (all agents: advisor, TCO, comparison, report, research) |
| PDF          | WeasyPrint                                                       |
| Frontend     | React 18 + Vite, Tailwind CSS, Recharts, React Router v6, Axios  |
| Infra        | Docker Compose                                                   |

---

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env          # then add your ANTHROPIC_API_KEY
docker compose up
```

- Backend / API docs: <http://localhost:8000/docs>
- Frontend: <http://localhost:5173>

> **First run:** open the frontend and **register an account** at `/register`.
> All projects, scenarios, and reports are scoped to your login — you'll be
> redirected to the login screen until you do.

### Local development (without Docker)

**Backend** (managed by [uv](https://docs.astral.sh/uv/)):
```bash
cd backend
uv sync                      # creates .venv and installs locked deps
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Tests & quality checks

```bash
# Backend — lint, format, types, security, tests
cd backend
uv run ruff check app tests alembic
uv run black --check app tests alembic
uv run isort --check-only app tests alembic
uv run mypy app --ignore-missing-imports
uv run bandit -r app alembic -ll
uv run pytest

# Frontend — lint and production build
cd frontend
npm run lint
npm run build
```

Tooling config for `ruff`, `black`, and `isort` lives in the root
`pyproject.toml`; ESLint config is `frontend/eslint.config.js`.

---

## Project Structure

```
NetPlanner/
├── docs/
│   ├── PID.md           # Project Initiation Document — the build contract
│   └── RUNBOOK.md       # Setup, quality gate, and the build journal
├── backend/             # FastAPI app, ORM models, schemas, agents, routes
│   ├── app/
│   │   ├── agents/      # AI agents (project context, research, TCO, ...)
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── routes/      # API route handlers
│   │   ├── schemas/     # Pydantic schemas + agent handoff contracts
│   │   └── services/    # PDF generation, etc.
│   ├── alembic/         # Database migrations
│   └── tests/           # pytest eval suite
├── frontend/            # React + Vite SPA
└── docker-compose.yml
```

---

## Build Plan

| Phase | Deliverable                                               | Status   |
|-------|-----------------------------------------------------------|----------|
| 0     | Project scaffold — FastAPI, React, SQLite, Docker Compose | ✅ Done   |
| 1     | Projects CRUD (backend routes + frontend UI)              | ✅ Done   |
| 2     | Research Agent + Advisor with streaming (core AI layer)   | ✅ Done   |
| 3     | TCO Calculator (form, agent, chart visualization)         | ✅ Done   |
| 4     | Vendor Comparison (form, agent, matrix UI)                | ✅ Done   |
| 5     | Report generation (PDF export via WeasyPrint)             | ✅ Done   |
| 6     | Polish pass — design refinement, error states, eval run   | ✅ Done   |
| 7     | Mid-cycle refresh + version snapshots + comparison (1.5)  | ✅ Done   |

**Current status: v1 launched, Phase 7 shipped.** Six launch phases plus
the PID amendment 1.5 additions (mid-cycle refresh, version snapshots, TCO
comparison) are complete. **218 backend tests at ~93% coverage**, and **all
7 PID eval cases still pass** unchanged (the PIS-10 acceptance gate — 6/7
required, both zero-tolerance evals included). See
[`docs/RUNBOOK.md`](docs/RUNBOOK.md) for the eval results and the full
build journal, including the Phase 7 entry.

---

## Security

This build follows the Secure Build Standard. Notably:

- **Auth (SEC-01 / SEC-17).** Argon2id-hashed passwords; session JWT
  delivered as an httpOnly, Secure, `SameSite=Strict` cookie (Backend-for-
  Frontend pattern). Logout server-side rotates a `session_version` counter,
  invalidating any prior tokens.
- **Ownership (SEC-03 / SEC-27).** Every project, TCO scenario, comparison,
  conversation, and report is scoped to the authenticated user. Cross-user
  access returns 404 — never confirms whether the resource exists.
- **Rate limiting (SEC-06).** SlowAPI in-process limiter on the LLM/PDF-heavy
  endpoints (Advisor, Comparison, Reports), keyed by user id / IP. 429
  responses carry `Retry-After`.
- **Prompt injection (AI-1).** Project context is placed inside an explicit
  untrusted-data fence in the Advisor system prompt, after the PIS-17 anchor
  and PIS-24 guardrails. Boundary markers in hostile fields are escaped.
- **PDF sanitization (AI-1).** Advisor markdown is bleach-sanitized before
  rendering; WeasyPrint's url_fetcher rejects all external/local fetches.
- **Immutable reports.** Each report stores its rendered PDF bytes; a
  re-download returns the original artifact verbatim.
- **Production startup.** The DB must be at the Alembic head — `create_all`
  fallback is disabled in production. `JWT_SECRET` must be set.
- **Secrets.** Read from environment only; never committed; never logged.

- **CSRF (SEC-07).** State-changing requests carry a double-submit CSRF
  token: a non-httpOnly `netplanner_csrf` cookie is echoed back in an
  `X-CSRF-Token` header and verified with a constant-time comparison, on top
  of the `SameSite=Strict` session cookie.
- **Brute-force defense (SEC-06 / SEC-28).** Accounts lock for 15 minutes
  after 5 consecutive failed logins; login success, failure, and logout are
  written to a dedicated audit log (no passwords or PII).
- **Transport headers (SEC-08 / SEC-24).** HSTS is sent automatically in
  production; API responses set `Cache-Control: no-store` and a deny-all CSP.

Single-instance SQLite is the launch default. For multi-user deployments
beyond ~50 active operators, point `DATABASE_URL` at Postgres (the migration
tree is dialect-agnostic).

---

## License

NetPlanner is released under the [MIT License](LICENSE).
Copyright © 2026 Elliot Conner / The Tech-E LLC.

---

_NetPlanner is a personal tool built to production quality by Elliot Conner /
The Tech-E LLC._
