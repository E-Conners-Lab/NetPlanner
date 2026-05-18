# NetPlanner

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
- **Vendor Comparison** — 2–3 platforms compared across your criteria, with
  live pricing research and `confirmed` / `estimated` / `unavailable`
  confidence indicators.
- **Reports** — export any combination of artifacts as a formatted PDF.

All pricing data carries a confidence tag, and every PDF carries a disclaimer:
estimates are for planning only — verify with vendors before budget submission.

---

## Tech Stack

| Layer        | Stack                                                            |
|--------------|------------------------------------------------------------------|
| Backend      | Python 3.12, FastAPI, SQLAlchemy (async) + SQLite, Alembic, Pydantic v2 |
| AI           | Anthropic Python SDK — Sonnet (advisor/TCO/comparison/report), Haiku (research) |
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

### Local development (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
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
ruff check app tests alembic
black --check app tests alembic
isort --check-only app tests alembic
mypy app --ignore-missing-imports
bandit -r app alembic -ll
pytest

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
├── docs/PID.md          # Project Initiation Document — the build contract
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

| Phase | Deliverable                                                        |
|-------|--------------------------------------------------------------------|
| **0** | Project scaffold — FastAPI, React, SQLite, Docker Compose          |
| 1     | Projects CRUD (backend routes + frontend UI)                       |
| 2     | Research Agent + Advisor with streaming (core AI layer)            |
| 3     | TCO Calculator (form, agent, chart visualization)                  |
| 4     | Vendor Comparison (form, agent, matrix UI)                         |
| 5     | Report generation (PDF export via WeasyPrint)                      |
| 6     | Polish pass — design refinement, error states, eval run            |

**Current status: Phase 0 complete.** Route handlers are stubs that return
`{"status": "not implemented"}`; agent functions raise `NotImplementedError`.

---

## Security

This build follows the Secure Build Standard. Notably: secrets are read from
the environment only (never committed), all inputs are validated server-side
with Pydantic, error responses never leak internals, and the backend container
runs as a non-root user from a slim base image.

---

_NetPlanner is a personal tool built to production quality by Elliot Conner /
The Tech-E LLC._
