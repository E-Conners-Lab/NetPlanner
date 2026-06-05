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

### Post-launch dependency notes

- **recharts 2 → 3** (commit `db8ca22`, verified 2026-05-19). `TcoChart` (the only recharts component) renders intact under v3 — stacked `BarChart`, axes, grid, legend, and the custom `TcoTooltip` all work without code changes. Verified by rendering the component in headless Chromium with representative 5-year data: 0 console errors, tooltip payload still exposes `entry.fill`/`name`/`value`/`dataKey`, computed total row correct. No follow-up required.

### Phase 7 — Mid-cycle refresh + version snapshots + TCO comparison

**Approved as PID amendment 1.5 (2026-05-25).** Closed the "what about phased refresh inside the lifecycle?" gap surfaced in a stakeholder conversation, and added version snapshots so an existing scenario can be revised without overwriting the artifact that was already shared with finance.

**Shipped (additive, no breaking changes):**

- **Refresh events.** `TCOFormInputs.refresh_events: list[RefreshEvent]` (default `[]`). Each event carries `year` ∈ [2, 5], `percent_of_devices` ∈ (0, 100], and an optional `cost_per_unit_override`. The deterministic engine adds a `refresh_hardware` line in the targeted year only; licensing/support/adjacent recurring stay flat (refreshed units re-use the existing fleet line). Out-of-window events are flagged AND excluded from totals — never silently rolled in.
- **Version snapshots.** `TCOScenario` gains `lineage_id` (indexed, **not** an FK so a deleted version doesn't cascade through the lineage) and `version` (1-indexed). Saving with `parent_scenario_id` inherits the parent's lineage and increments version; saving without it starts a new lineage anchored to the row's own id. The Alembic migration (`a3d1f7c52e84`) backfills every existing row to `lineage_id = id, version = 1` — pre-amendment scenarios become v1 of their own single-version lineage.
- **Convenience route.** `GET /projects/{id}/tco/lineages/{lineage_id}` returns the version history scoped to the project (SEC-27 — cross-project access returns `[]`, never reveals existence elsewhere).
- **Edit-as-version UX.** An "Edit" affordance on a saved scenario opens the form pre-filled and threads `parent_scenario_id` through the next save automatically — the user never has to choose "new vs. version", and the existing scenario row stays intact.
- **Dashboard grouping.** The TCO page groups saved scenarios by lineage with a `v3 (3 versions)` badge and collapses history by default after 5 versions to keep noise low.
- **Screen-first comparison.** A new `TcoCompare` card on the TCO page picks two scenarios (any project, any lineage), overlays them in a Recharts `<LineChart>` with two series, and emits a per-year delta table plus an assumption-diff list. No new backend call — data already in the saved-scenarios listing.
- **PDF artifact for comparison.** `ReportArtifact` gains a new kind `tco_comparison` with paired `ref_id` + `ref_id_b`. Pydantic rejects same-id or missing pairs. The report renderer adds a side-by-side TCO Comparison block with a 5-year-total delta row.
- **Report version picker.** Each TCO scenario in the report builder shows its `vN` badge and a `latest` chip for the newest version of each lineage. PDF TCO headers now read `v3 · saved 2026-05-25` so a finance reader can tell which revision they're looking at.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 7.1 | First Alembic migration failed under SQLite because the new `lineage_id` / `version` columns were `NOT NULL` from the start | SQLite cannot add a NOT NULL column without a server default | Migration now adds them nullable, backfills `lineage_id = id` / `version = 1`, then enforces NOT NULL via `batch_alter_table` |
| 7.2 | `resolve_artifacts` returned a 4-tuple, callers expected the new comparison list | New `tco_comparison` kind needs its own bucket in the return tuple; both routes that consumed the tuple had to be updated | Switched to a named 5-tuple return + updated `routes/reports.py` (both `create_report` and `download_report`) — caught by the route test for re-download |
| 7.3 | `_render_tco` test fixtures broke after adding `version` / `created_at` to the PDF header | Tests built `TCOScenario` directly without persisting; ORM defaults don't fire until `INSERT` | Updated the test factory to pass `id`, `lineage_id`, `version`, `created_at` explicitly |

**Quality gate:** 136 backend tests pass (up from 111), coverage at **95.68%** (`app/schemas/tco.py`, `app/services/tco_service.py`, `app/routes/tco.py` each at 100%). All seven PID evals still pass — Eval 1 ($218,000 5-year total) is byte-for-byte unchanged because `refresh_events` defaults to empty. Ruff, black, isort, mypy, bandit, and `alembic check` all clean. Frontend lint + production build clean.

### Phase 8 — Release-readiness security pass (2026-05-26)

A pre-public-release audit found ten items spanning auth, dependency risk,
PDF sanitization, rate limiting, prompt-injection boundaries, schema limits,
production startup, report immutability, version-race correctness, and CI
gates. All ten landed in one pass under SEC-01/02/03/16/17/27, AI-1, and
SEC-29/35.

**Shipped (additive where possible, breaking only where SEC-03 ownership
required it):**

- **Auth + identity layer.** New `User` ORM model with Argon2id-hashed
  credentials (SEC-17, OWASP 2026 baseline `m=19 MiB, t=2, p=1`). JWT session
  delivered exclusively via an httpOnly, Secure-by-default,
  `SameSite=Strict` cookie (SEC-01, BFF pattern). `session_version` per user
  is bumped on logout / password change so prior tokens stop validating
  server-side (SEC-16). Routes: `POST /auth/register`, `POST /auth/login`,
  `POST /auth/logout`, `GET /auth/me`. SPA gains an `AuthProvider`,
  `ProtectedRoute`, and login/register pages.
- **Ownership scoping.** `Project.owner_id` (FK → `users.id`, `ON DELETE
  CASCADE`). Every project read/write filters on `owner_id`; every
  project-scoped sub-route resolves through `project_service.get_project`,
  so a TCO scenario / comparison / conversation / report under a project
  owned by another user is unreachable. Cross-user access returns 404
  (SEC-27 — never confirms existence). Test suite hardened with
  `test_authz_cross_user.py` covering every read/write path.
- **starlette CVE.** PYSEC-2026-161 fixed by bumping `starlette==1.0.0 →
  1.0.1` in `uv.lock`. `pip-audit` clean.
- **Report sanitization.** Advisor-authored markdown is now passed through
  `bleach.clean` with a tight tag whitelist (no `<script>`, `<img>`,
  `<iframe>`, `<object>`, `<a href=…>`); raw HTML, `file://`, `javascript:`,
  remote image URLs, and inline event handlers are stripped before the PDF
  renderer sees them. WeasyPrint's `url_fetcher` is replaced with a
  blocking fetcher so anything that slipped past bleach still cannot reach
  off-document.
- **Rate limiting (SEC-06).** SlowAPI in-process limiter keyed by
  authenticated user id (or stable token hash / IP for anon callers).
  Limits — Advisor 10/min, Comparison 5/min, Report create 6/min, Report
  download 15/min, Auth login 10/min, Auth register 5/min. 429 returns a
  structured JSON body with `Retry-After`. Limiter is opt-out for tests via
  `NETPLANNER_RATE_LIMIT_ENABLED=0` and re-enabled by the
  `rate_limited_client` fixture.
- **Prompt-injection boundary (AI-1, PIS-17).** Advisor system prompt order
  is anchor → guardrails → guidance → explicit "UNTRUSTED data" preamble →
  `<<PROJECT_CONTEXT>>…` fence. Project fields are escaped so a hostile
  description containing the fence-close marker cannot break out and rewrite
  the system role. Tests in `test_advisor_prompt_injection.py` assert the
  anchor is always first and that hostile fence-close attempts are masked.
- **Schema caps (SEC-05).** Project description/existing_infra capped at
  4000; Advisor `message` at 4000; comparison vendor names (120) /
  criterion strings (200) / criterion count (10); report `artifacts` count
  (20); TCO `device_count` (1e6), per-unit costs (1e7), lump sums (1e9),
  `refresh_events` count (10); project `budget_ceiling` (1e12). Frontend
  login/register forms enforce the same email/password caps.
- **Production DB lifecycle.** `init_db` no longer falls back to
  `Base.metadata.create_all()` in production — it reads `alembic_version`
  and fails loud if the schema is not at head. Development keeps the
  forgiving first-run behavior so `docker compose up` works on a fresh
  clone. Docker entrypoint scope: operators run `alembic upgrade head`
  before the app starts.
- **Immutable report snapshots.** `Report.pdf_blob` stores the PDF bytes at
  create time. Re-download returns the snapshot verbatim — the TCO numbers
  finance signed off on never silently change if the source scenario is
  later edited or deleted. The renderer is not called again on re-download.
- **User-submitted report title.** The Report Agent accepts an explicit
  `title=` argument; the PDF header uses it instead of the legacy
  `"NetPlanner Report — {project.name}"`. Filename slug also derives from
  the user title.
- **Advisor summarization (PIS-16).** `conversation_service.maybe_summarize_history`
  triggers at ≥15 messages and folds the oldest 10 into
  `Conversation.summary` (deterministic compression — the swap-in point for
  an LLM-backed summarizer if we want one later). The Advisor's system
  prompt embeds the summary after the project-context fence.
- **TCO version-race fix.** Unique `(lineage_id, version)` constraint on
  `tco_scenarios` (Alembic + ORM `UniqueConstraint`). `save_scenario` now
  retries on `IntegrityError` so a race-loser re-reads
  `max(version) + 1` and tries again instead of crashing with a 500.
- **Transport polish.** HSTS is now opt-in via `ENABLE_HSTS=1` so local
  HTTP dev does not pin browsers to HTTPS-only for a year. `/health`
  remains a no-DB liveness probe; new `/ready` exercises the DB so
  orchestrators can gate traffic. `RequestIDMiddleware` echoes /
  generates an `X-Request-ID` per request and emits a structured access
  log line (method/path/status/duration_ms/request_id).
- **CI security gates blocking.** `pip-audit`, `npm audit` (`--audit-level=moderate`),
  Semgrep, and TruffleHog all lost their `continue-on-error: true`. `pyjwt`
  bumped to `2.12.0` to clear PYSEC-2026-120; semgrep `directly-returned-format-string`
  false-positive marked with `nosemgrep` (this is a rate-limit key, not a
  Flask response body).

**Database & operations:**

- New SQLite remains acceptable for single-tenant launch — every artifact
  is scoped to a single user, so concurrent-write hot spots are minimal.
  For multi-user deployments above ~50 active operators, switch
  `DATABASE_URL` to `postgresql+asyncpg://…` and run `alembic upgrade head`
  in production. The Alembic tree is dialect-agnostic except for the
  legacy-owner backfill, which uses `CURRENT_TIMESTAMP` (both dialects).
- New env vars: `JWT_SECRET` (required in production), `SESSION_COOKIE_SECURE`
  (default true; flip to false for local plain HTTP), `SESSION_COOKIE_NAME`,
  `SESSION_MAX_AGE_SECONDS`, `ENABLE_HSTS`. See `.env.example`.

**Issues encountered and fixed:**

| # | Issue | Cause | Fix |
|---|---|---|---|
| 8.1 | First migration autogenerate flagged a unique-index drift on `users.email` | The ORM marks `email` as `unique=True, index=True`; the hand-written migration created the index without `unique=True` | Set `unique=True` on the `ix_users_email` index in the migration; `alembic check` clean |
| 8.2 | `concurrent_version_save_with_collision` test crashed with `IllegalStateChangeError` from SQLAlchemy | Two coroutines calling `db.commit()` on a single AsyncSession is unsupported | Rewrote the test as an out-of-band intruder row + a single retry call; the IntegrityError-retry path is exercised cleanly |
| 8.3 | `pip-audit` flagged `pyjwt==2.10.1` after the auth layer landed | PYSEC-2026-120 affects pyjwt < 2.12.0 | Bumped to `2.12.0` in `pyproject.toml`; `uv lock` regenerates the lockfile |
| 8.4 | Semgrep flagged `return f"user:{user_id}"` as a Flask format-string XSS | False positive — the function builds a rate-limit key, not a response body | Marked the lines with `# nosemgrep` and documented the context |

**Quality gate:**

| Check | Result |
|---|---|
| `ruff check app tests alembic` | clean |
| `black --check app tests alembic` | clean |
| `isort --check-only app tests alembic` | clean |
| `mypy app --ignore-missing-imports` | clean |
| `bandit -r app alembic -ll` | clean (low only) |
| `alembic upgrade head && alembic check` | clean |
| `pytest --cov=app --cov-fail-under=80` | **206 passed**, 1 skipped, **92.35% coverage** |
| `pip-audit -r <lockfile>` | clean |
| `npm run lint && npm run build` | clean |
| `npm audit --audit-level=moderate` | 0 vulnerabilities |
| `semgrep scan --config=auto --error` | 0 findings |

All seven PID evals still pass (the test runner exercises Eval 1, 4, 6, 7
automatically; Eval 2/3/5 remain manual review per PIS-09). The PIS-10
acceptance gate (6/7, both zero-tolerance evals passing) is preserved.

### Phase 9 — Open-source release hardening (2026-06-05)

A pre-publication scan (secrets/history sweep + parallel security, OSS-readiness,
and dependency audits) confirmed the repo was close to release-ready — clean git
history, no committed secrets, MIT licensed — and surfaced a punch-list of gaps
against the Secure Build Standard. All closed in one pass.

**Shipped:**

- **CSRF double-submit (SEC-07).** New `CSRFMiddleware` enforces an
  `X-CSRF-Token` header (constant-time compared, SEC-26) against a readable
  `netplanner_csrf` cookie on every mutating `/api` request; safe methods seed
  the cookie, and `GET /auth/csrf` gives the SPA a reliable seed point. Axios
  attaches the header for unsafe methods; `useStream` does the same for the SSE
  POST. Enforcement is opt-out for the suite via `NETPLANNER_CSRF_ENABLED=0`,
  re-enabled in `test_csrf.py`.
- **Bearer fallback removed (SEC-01).** `auth._extract_token` and the rate-limit
  key func now read the session JWT only from the httpOnly cookie — no
  `Authorization: Bearer` path that could tempt a client to hold the token in
  JS-readable memory.
- **Account lockout + audit log (SEC-06 / SEC-28).** Five consecutive failed
  logins lock an account for 15 minutes (`users.failed_login_count` /
  `locked_until`, migration `b7e2c4f9a1d3`); the lock is not revealed to the
  caller (generic 401, SEC-18). A dedicated `app.audit` logger records login
  success/failure/lock and logout — keyed by `user_id` or a salted email
  fingerprint, never raw PII or passwords.
- **Transport headers (SEC-08 / SEC-09 / SEC-24).** HSTS now emits
  automatically in production (no longer a forgettable flag); API responses
  carry `Cache-Control: no-store` and a deny-all `Content-Security-Policy`.
- **Dependency + repo hygiene.** `react-router-dom 6.30.3 → 6.30.4` clears
  `GHSA-2j2x-hqr9-3h42` (open redirect); `.claude/` untracked and gitignored;
  `AGENTS.md` find-replace artifacts fixed; README gains a License section.

**Quality gate:** ruff / black / isort / mypy clean; `bandit -ll` clean;
`alembic upgrade head && alembic check` clean; **pytest 213 passed, 1 skipped,
92.92% coverage**; frontend ESLint + build clean; `npm audit` 0 vulnerabilities.

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
| App refuses to boot in production with `RuntimeError: Database has not been initialized` | `init_db` now requires the DB to be at the Alembic head (it no longer falls back to `create_all`) | Run `alembic upgrade head` before launching, or fix the running revision drift |
| `RuntimeError: JWT_SECRET is required in production` at startup | Auth needs a strong, persistent signing key — empty default is rejected when `ENVIRONMENT=production` | Set `JWT_SECRET` to a long random value: `python -c "import secrets;print(secrets.token_urlsafe(48))"` |
| Login succeeds but every subsequent call returns 401 | `SESSION_COOKIE_SECURE=true` but the deployment is HTTP-only | Set `SESSION_COOKIE_SECURE=false` for local dev, or terminate TLS so `Secure` cookies actually round-trip |
| Browser pinned to HTTPS on local dev | `ENABLE_HSTS=1` was set and the browser cached `Strict-Transport-Security` for a year | Clear HSTS for the host in the browser; leave `ENABLE_HSTS=0` unless production HTTPS is wired up |
| `429 Too many requests` during testing | Rate limiter (SEC-06) is firing on the per-user / per-IP window | For local exploration, restart the server (in-process counters reset); for tests, the suite-wide `NETPLANNER_RATE_LIMIT_ENABLED=0` flag keeps the limiter off |
| `403 CSRF validation failed` on a POST/PUT/DELETE | The request lacks a matching `X-CSRF-Token` header (SEC-07) | In the SPA this is automatic; for manual `curl`/Postman, `GET /api/auth/csrf` first, then echo the `netplanner_csrf` cookie value in the `X-CSRF-Token` header. The suite-wide `NETPLANNER_CSRF_ENABLED=0` flag keeps enforcement off for tests |
| Account returns `Invalid email or password` for a known-good password | Five consecutive failed logins locked the account for 15 minutes (SEC-06) | Wait out the 15-minute window, or clear `failed_login_count` / `locked_until` on the `users` row in dev |

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
| 7 | Mid-cycle refresh + version snapshots + TCO comparison (PID amendment 1.5) | ✅ Complete |
| 8 | Release-readiness security pass (auth, ownership scoping, rate limiting, immutable reports, prompt-injection boundary, schema caps, production DB lifecycle, CI security gates) | ✅ Complete |

NetPlanner v1 cleared the PID acceptance gate (7/7 evals); Phase 7 added the refresh / versioning / comparison capabilities behind PID amendment 1.5 without breaking any existing contract; Phase 8 made the app safe for public release (auth, ownership scoping, dependency CVE patch, rate limiting, immutable report snapshots, hardened PDF rendering).

### Planned enhancements (post-v1)

Scoped but deferred to keep the v1 launch on the PID's defined capabilities.
Each would land via a PID amendment.

| Item | Description |
|---|---|
| Itemized hardware BOM | Replace the flat per-unit hardware cost with a bill-of-materials line-item list — chassis, line cards, SFP/QSFP transceivers, PSUs — so accessory costs are captured. A deterministic calculator change plus a repeatable line-item form. |
| AI accessory suggestion | Given a device model or category, suggest a draft accessory BOM (line-card and transceiver options with estimated, confidence-tagged pricing) for the user to review and edit before it feeds the TCO. |
