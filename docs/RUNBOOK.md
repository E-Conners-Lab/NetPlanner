# NetPlanner — Build & Operations Runbook

A living document. It exists so that **anyone can reproduce this build from a
clean machine**, and so the build process — including every issue hit and how
it was resolved — is captured as it happens.

- **Setup & operations** (Sections 1–5) — how to install, run, and verify.
- **Build journal** (Section 6) — phase-by-phase log of what was built and
  every issue encountered and fixed. Appended every phase.
- **Troubleshooting** (Section 7) — symptom → cause → fix, distilled from the
  journal.

> Keep this file current. Each phase appends a journal entry; each non-trivial
> error appends a troubleshooting entry.

---

## 1. What NetPlanner Is

An AI-powered business decision support tool for network engineers — TCO
models, vendor comparisons, and stakeholder-ready PDF reports. The build
contract is [`docs/PID.md`](PID.md). The six-phase plan is in the
[`README`](../README.md); current status: **Phase 1 complete**.

---

## 2. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | 3.13 works; the Docker image pins 3.12-slim |
| Node.js | 20+ | for the React frontend |
| Docker + Compose | recent | optional — only for the containerized path |
| git, gh | any | `gh` only needed to manage the GitHub repo |

A C toolchain plus Pango/Cairo libraries are needed for WeasyPrint (Phase 5).
The backend Docker image installs them already; for local PDF work on macOS:
`brew install pango`.

---

## 3. Reproducible Setup

Clone, then choose **one** path.

### 3a. Docker (recommended — one command)

```bash
cp .env.example .env          # add ANTHROPIC_API_KEY for Phase 2+; empty is fine for Phase 0/1
docker compose up
```

- API + docs: <http://localhost:8000/docs>
- Frontend:   <http://localhost:5173>

The `backend` service runs uvicorn with auto-reload; `frontend` runs the Vite
dev server. SQLite persists in `backend/data/` (bind-mounted).

### 3b. Local — backend

The backend is managed by [uv](https://docs.astral.sh/uv/) — `uv.lock` is the
committed source of truth.

```bash
cd backend
uv sync                              # creates .venv, installs locked deps
uv run alembic upgrade head          # creates backend/data/netplanner.db
uv run uvicorn app.main:app --reload # http://localhost:8000
```

> `uv sync` installs the `dev` dependency group (lint/type/security/coverage
> tooling) as well as runtime deps. `uv sync --no-dev` — used by the Docker
> image — installs runtime deps only.

### 3c. Local — frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

The Vite dev server proxies `/api` → `http://localhost:8000`, so run the
backend alongside it.

---

## 4. Quality Gate

Every section of work must pass this gate before it is considered done. Run it
incrementally, not just at the end.

### Backend (`cd backend`)

```bash
uv run ruff check app tests alembic              # lint
uv run black --check app tests alembic           # formatting
uv run isort --check-only app tests alembic      # import order
uv run mypy app --ignore-missing-imports         # type check
uv run bandit -r app alembic -ll                 # security (medium+)
uv run pytest --cov=app --cov-report=term-missing # tests + coverage (target 80%+)
```

Tooling config: `ruff`/`black`/`isort` in the root `pyproject.toml`,
coverage in `backend/.coveragerc`, pytest in `[tool.pytest.ini_options]` of
`backend/pyproject.toml`. Dependencies and the `dev` group live in
`backend/pyproject.toml`; `backend/uv.lock` pins exact resolved versions.

**CI** — `.github/workflows/ci.yml` runs this whole gate on every push to
`main` and every PR: the backend gate (lint/type/security/tests + migration
drift), the frontend gate (lint/build), and security scans (`pip-audit`,
`npm audit`, Semgrep SAST, TruffleHog secret scan). The core gate is
hard-blocking; the security scans are informational until their baseline is
triaged (see the file's header comment).

### Frontend (`cd frontend`)

```bash
npm run lint      # ESLint 9 flat config (eslint.config.js)
npm run build     # production build must succeed
```

### Database migrations

```bash
cd backend
alembic upgrade head        # apply
alembic downgrade base      # roll back
alembic check               # verify migrations match the ORM models (no drift)
```

---

## 5. Project Layout

```
NetPlanner/
├── docs/            PID.md (contract), RUNBOOK.md (this file)
├── backend/         FastAPI app, SQLAlchemy models, agents, routes, tests
├── frontend/        React + Vite SPA
├── docker-compose.yml
└── pyproject.toml   shared Python tooling config
```

See the `README` for the full tree.

---

## 6. Build Journal

Newest phase last. Each entry: what shipped, then every issue hit and its fix.

### Phase 0 — Project Scaffold

**Shipped:** FastAPI app skeleton (CORS, lifespan, route stubs), async
SQLAlchemy + SQLite, all ORM models and Pydantic schemas (including the PIS-15
agent handoff contracts), agent stubs, Alembic with the initial migration, the
React + Vite frontend shell, Docker Compose, and the test scaffold. The full
backend + frontend quality gate was established and made green.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 0.1 | `PID.md` was at the repo root | Expected at `docs/PID.md` by the build spec | Moved it (content unchanged) |
| 0.2 | `venv/bin/python -m pip` failed — "No module named pip" | The pre-existing venv is uv-managed and ships no pip | Used `uv pip install` |
| 0.3 | venv is Python 3.13, spec says 3.12 | Pre-existing venv | Set `requires-python = ">=3.12"` — code runs on both; Docker pins 3.12-slim |
| 0.4 | `docker compose up` would fail before `.env` exists | `env_file: .env` is required by default | Made it `required: false` |
| 0.5 | Frontend production Dockerfile used `npm ci` with no lockfile | `npm ci` requires a committed `package-lock.json` | Generated and committed the lockfile via `npm install` |
| 0.6 | `ruff` flagged B008 on `Depends()` in argument defaults | B008 is a known false positive for FastAPI's DI idiom | `extend-immutable-calls = ["fastapi.Depends", ...]` in `pyproject.toml` |
| 0.7 | `ruff` and `isort` disagreed on import ordering | `isort` did not know `app` was the first-party package | `known_first_party`/`known-first-party = ["app"]` for both |
| 0.8 | `ruff` UP037 stripped quotes from SQLAlchemy `Mapped["X"]` forward refs | `from __future__ import annotations` makes the quotes redundant to ruff | Verified safe — `configure_mappers()` resolves relationships from the registry; kept the change |
| 0.9 | `alembic/env.py` import block flagged as unsorted | It imports `app` only after a `sys.path` insert — order is intentional | Per-file ignore for ruff; `extend_skip_glob` for isort |
| 0.10 | `config.py` had `anthropic_api_key: str = ""` — a silent empty secret | Violates the fail-fast secret rule | Added `require_anthropic_api_key()` accessor that raises if unset; the AI layer must call it |
| 0.11 | ESLint flagged 14 unused `import React` | Vite's automatic JSX runtime makes the import dead | Removed them (kept `main.jsx`, which uses `React.StrictMode`) |
| 0.12 | ESLint `react-hooks/exhaustive-deps` on `useStream` | `useCallback` referenced `stop` but omitted it from deps | Moved `stop` above `start` (avoids the temporal dead zone), added it to the dependency array |

### Phase 1 — Projects CRUD + Project Context Agent

**Shipped:** Backend Projects CRUD (`project_service` data layer + 5 REST
endpoints), the Project Context Agent (ORM → `ProjectContext` handoff
contract), and the frontend Projects UI (Dashboard with create modal,
ProjectDetail with edit + delete-confirmation, reusable Modal / ConfirmDialog /
ProjectForm / ProjectCard, and the project hooks + API layer). Built TDD —
18 tests written first (RED), then implementation (GREEN). Coverage 89%
(Phase 1 code 100%). Verified with a live end-to-end CRUD cycle against a real
uvicorn server.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 1.1 | Project Context Agent test failed — `None` for string fields | A transient ORM object has no column defaults; they apply only on DB insert | Test constructs a record mirroring a DB row (empty strings, not `None`) |
| 1.2 | `coverage.py` reported 53% on code the tests clearly exercised | SQLAlchemy's async engine bridges sync/async via greenlet; coverage loses tracing through it | Added `backend/.coveragerc` with `concurrency = greenlet,thread` → true 100% |
| 1.3 | `ruff` and `isort` disagreed again, on test files only | `ruff` did not treat `app` as first-party from files outside the `app/` package | Added `known-first-party = ["app"]` to ruff's isort settings |
| 1.4 | `mypy`: handlers annotated `-> ProjectRead` returned ORM `Project` | FastAPI converts via `response_model`; the annotation was inaccurate | Annotated the true return type (`Project`); `response_model=ProjectRead` is the API contract |
| 1.5 | Frontend delete failure was silently swallowed | `catch {}` closed the dialog without informing the user | Added an `error` prop to `ConfirmDialog`; `ProjectDetail` surfaces the failure and keeps the dialog open for retry |

### Phase 2 — Research Agent + Advisor streaming (core AI layer)

**Shipped:** The Research Agent (Haiku 4.5 + Anthropic's server-side
`web_search` tool, confidence-tagged results); the Advisor Agent (Sonnet 4.6,
streaming, multi-turn, invokes Research as a tool — PIS-13 — with the PIS-17
spec anchor, PIS-24 guardrails, and a 20-message history cap — PIS-16);
conversation persistence; the advisor route (SSE `text/event-stream`); and the
frontend Advisor chat UI (`Advisor.jsx` + a real `useStream` SSE hook). Built
test-first — 21 new mocked tests (no API calls in CI), 39 total, 92% coverage.
Eval 7 (vague input → request context) is automated and passing; Eval 2 was
verified live — the Advisor produced CapEx/OpEx framing, a sourced pricing
figure, an ROI narrative, alternatives, and confidence tags.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 2.1 | `anthropic` SDK pinned at `0.40.0` | Predated streaming / web-search / adaptive-thinking support | Bumped to `0.102.0`; re-pinned in `requirements.txt` |
| 2.2 | PID named `claude-sonnet-4-5` — now a legacy model ID | Models released after the PID was written | Updated to `claude-sonnet-4-6` via **PID amendment 1.1** (same cost basis) |
| 2.3 | API key valid in `.env` but every call returned `401` | `ANTHROPIC_API_KEY` exported in `~/.zshrc` shadowed `.env` — pydantic-settings gives OS env vars precedence over `.env` | Commented out the `~/.zshrc` export so `.env` is authoritative; precedence is correct and was left as-is |
| 2.4 | `mypy` rejected plain dict literals for `tools` / `messages` | The Anthropic SDK types those params as strict `TypedDict`s | Targeted `# type: ignore[list-item/arg-type]` — the SDK accepts dicts at runtime |
| 2.5 | Advisor UI: stream-error dismiss button did nothing | Dead `localError` state; `useStream`'s `error` had no external clear | Added `clearError` to `useStream`; removed the dead state |
| 2.6 | Advisor UI used a `window` CustomEvent bus for suggestion chips | Sub-agent over-avoided one level of prop passing | Replaced with an `onSuggest` prop callback |

### Phase 3 — TCO Calculator

**Shipped:** A **deterministic** TCO calculator (`agents/tco.py`) — year-by-year
cost model, the PIS-21 reasonableness check, and factual assumptions; the TCO
persistence service; the TCO routes (`preview` computes without saving, `POST`
computes and saves, `GET` lists); and the frontend TCO page (input form with
client-side validation, a Recharts stacked-bar chart, year-by-year table,
warnings banner, and saved-scenario list). 56 backend tests, 94% coverage.
Evals 1, 4, and 6 are all automated and passing (the suite now has zero
skipped tests).

**Design note:** the TCO calculation is plain Python, not an LLM call —
PIS-09 requires Evals 1/6 to be exact unit tests, and a financial model must
never produce wrong arithmetic. The "agent" boundary is kept for the stable
`TCOResult` handoff contract, same pattern as the Project Context Agent.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 3.1 | PID Eval 1's stated 5-year total ($198,400) contradicted its own breakdown | The total summed only 4 years of licensing; Year 1 + four recurring years at $19,600 is $218,000 | Corrected to $218,000 via **PID amendment 1.2** (user-confirmed); the calculator and Eval 1 use $218,000 |
| 3.2 | Vite build warns "chunks larger than 500 kB" | `recharts` is a large dependency, now in the bundle | Advisory only — build still succeeds. Code-splitting is a Phase 6 polish item |

### Phase 4 — Vendor Comparison

**Shipped:** The Comparison Agent (`agents/comparison.py`) — single Sonnet
call that synthesizes a vendor x criterion matrix from per-vendor research,
with a guaranteed-complete matrix (any cell the model omits is filled
`unavailable`, so the matrix is never blank and an unsourced cell is never
`confirmed`). The comparison persistence service; the route (Research runs per
vendor in parallel, then the agent synthesizes — PIS-12/PIS-13); and the
frontend Comparison page (dynamic 2-3 vendor + criteria fields, the matrix
table with `ConfidenceBadge` per cell, saved comparisons). 67 backend tests,
94% coverage. Evals 3 and 5 are manual review (PIS-09); Eval 3 was verified
live.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 4.1 | Live Eval 3: the matrix generated but every cell was `unavailable` for well-known vendors | The agent prompt forbade *any* value without research backing — so stable facts (Meraki's subscription licensing, Mist's Marvis AI) were dropped too | Prompt now separates **pricing** (research-sourced for `confirmed`, else `estimated`/`unavailable`) from **capability facts** (the model may answer from knowledge, tagged `estimated`). Research query tightened to pricing-focus |
| 4.2 | Live test first hit a stale backend (Phase-0 comparison stub) | The dev `uvicorn` was started before Phase 4 and does not auto-reload | Restart the server after backend code changes — or run it with `--reload` |
| 4.3 | The comparison call (~30-60s) would race the axios 30s timeout | Frontend `client.js` has a 30s default | `generateComparison` overrides the timeout to 120s per-request |

### Phase 5 — Report generation (PDF)

**Shipped:** The Report Agent (`agents/report.py`) — **deterministic** HTML
assembly of a project's artifacts (TCO tables with a CSS cost-bar chart, the
comparison matrix with per-cell confidence, advisor conversations rendered
from markdown), with the mandatory disclaimer footer (PIS-23/24 #4) and full
HTML escaping. The PDF service (WeasyPrint, run in a worker thread); artifact
resolution + report persistence; the routes (`POST` returns the PDF as a
download, `GET` lists export history); and a new `GET /conversations`
endpoint. The frontend Reports page — artifact picker across TCO / comparison
/ conversation, PDF download, and export history. 81 backend tests, 95%
coverage.

**Design note:** like the TCO Agent, the Report Agent is deterministic
templating, not an LLM call — PIS-05 requires the PDF to render every table
"without truncation or formatting errors", and a report must never
hallucinate a number.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 5.1 | `import weasyprint` fails on macOS | WeasyPrint needs native Pango/Cairo libraries not installed by default | Lazy import keeps the app importable; the PDF test skips when they are absent; Docker installs them. Local fix: `brew install pango`, then run uvicorn/pytest with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (Homebrew libs are off the default dyld path on Apple Silicon) |
| 5.2 | The Reports UI needs to list advisor conversations as selectable artifacts, but no list endpoint existed | Phase 2 only tracked the active conversation client-side | Added `GET /projects/{id}/conversations` + `ConversationSummary` schema |
| 5.3 | A `422` from the PDF endpoint arrives as an unreadable `Blob` | The frontend requests the response with `responseType: 'blob'`, so error bodies are blobs too | Frontend reads `blob.text()` then `JSON.parse` to recover the `detail` |

### Phase 6 — Polish & launch readiness

**Shipped:** Security hardening — a `SecurityHeadersMiddleware` (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS) on every API response, a Content-Security-Policy plus headers on the frontend Nginx config, and `/docs` disabled in production; a review of the four AI Engineering Controls (AI-1–4 — all compliant, no fixes needed). An error-state consistency sweep, a design-consistency fix, and a bundle code-split. And the full seven-eval acceptance run.

**Eval run (PID Domain 2 / PIS-10 acceptance gate):**

| Eval | Type | Method | Result |
|---|---|---|---|
| 1 — TCO happy path | happy | automated | ✅ pass — $218,000 |
| 2 — Advisor justification | happy | manual | ✅ pass — CapEx/OpEx, pricing, ROI |
| 3 — Comparison matrix | happy | manual | ✅ pass — 10/10 cells, confidence tags |
| 4 — incomplete TCO input | edge (zero-tolerance) | automated | ✅ pass — 422, nothing saved |
| 5 — pricing unavailable | edge (zero-tolerance) | manual | ✅ pass — obscure vendor → `unavailable` |
| 6 — anomalous TCO cost | silent-failure | automated | ✅ pass — $6/unit flagged |
| 7 — vague advisor input | edge | automated | ✅ pass — requests context |

**7 of 7 pass** (PIS-10 requires 6/7; both zero-tolerance evals — 4 and 5 — pass). NetPlanner clears the PID's acceptance gate.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 6.1 | Eval 2's output did not reliably include explicit CapEx/OpEx framing — a named element of the eval's pass condition | The Advisor prompt asked for "budget narratives" but never named CapEx/OpEx | Added budget-justification guidance to the Advisor system prompt; Eval 2 re-run passes |
| 6.2 | Four components rendered errors as bare red text, not the app's red-banner style | Inconsistency across sub-components from different phases | Standardized all on the established red-banner error style |
| 6.3 | Frontend build warned "chunks larger than 500 kB" — a 632 kB monolith | `recharts` + the whole app in one bundle | Vite `manualChunks` splits `vendor-react` / `vendor-recharts`; warning gone |

---

## 7. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `No module named pip` in the venv | The backend venv is uv-managed and ships no pip — this is expected | Use `uv run <cmd>` and `uv sync`; never `pip` directly |
| `uv sync` warns `VIRTUAL_ENV does not match` | A stale `VIRTUAL_ENV` from an old venv is exported in the shell | Harmless — uv uses `backend/.venv` regardless; `unset VIRTUAL_ENV` to silence it |
| `docker compose up` errors on a missing `.env` | — | `cp .env.example .env` (Compose is also set to `required: false`) |
| `npm ci` fails in the frontend Docker build | `package-lock.json` missing | Ensure the lockfile is committed; run `npm install` to regenerate |
| Coverage shows 0% / low % on code that tests exercise | coverage not tracking SQLAlchemy's greenlet bridge | `backend/.coveragerc` must set `concurrency = greenlet,thread` |
| `ruff` and `isort` fight over import order | `app` not recognized as first-party | `known-first-party = ["app"]` in both tool configs |
| ESLint: `'React' is defined but never used` | Vite's automatic JSX runtime — no `import React` needed | Remove the import; import hooks directly |
| `cannot load library 'libgobject-2.0-0'` from WeasyPrint | Native Pango/Cairo libraries missing or off the dyld path (macOS) | `brew install pango`, then run with `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`; Docker already installs them on the default path |
| `alembic check` reports drift | ORM models changed without a migration | `alembic revision --autogenerate -m "..."` |
| Anthropic API returns `401 invalid x-api-key` despite a valid `.env` key | An `ANTHROPIC_API_KEY` exported in the shell shadows `.env` (env vars outrank `.env`) | Unset/fix the shell var, or run with `env -u ANTHROPIC_API_KEY`; Docker is unaffected |

---

## 8. Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 0 | Project scaffold | ✅ Complete |
| 1 | Projects CRUD + Project Context Agent | ✅ Complete |
| 2 | Research Agent + Advisor streaming (core AI layer) | ✅ Complete |
| 3 | TCO Calculator | ✅ Complete |
| 4 | Vendor Comparison | ✅ Complete |
| 5 | Report generation (PDF) | ✅ Complete |
| 6 | Polish — design, error states, full eval run | ✅ Complete |

All six phases complete — NetPlanner v1 is launch-ready (7/7 evals pass).

### Planned enhancements (post-v1)

Scoped but deferred to keep the v1 launch on the PID's defined capabilities.
Each would land via a PID amendment.

| Item | Description |
|---|---|
| Itemized hardware BOM | Replace the flat per-unit hardware cost with a bill-of-materials line-item list — chassis, line cards, SFP/QSFP transceivers, PSUs — so accessory costs are captured. A deterministic calculator change plus a repeatable line-item form. |
| AI accessory suggestion | Given a device model or category, suggest a draft accessory BOM (line-card and transceiver options with estimated, confidence-tagged pricing) for the user to review and edit before it feeds the TCO. |
