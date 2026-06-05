# Contributing to NetPlanner

Thanks for your interest in improving NetPlanner. This guide covers how to set
up a development environment, the quality bar a change must clear, and the
conventions we follow.

By participating you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Before you start

- For **bugs** and **feature ideas**, open an issue first so we can discuss the
  approach before you invest time. Use the issue templates.
- For **security issues**, do **not** open a public issue — see
  [SECURITY.md](SECURITY.md).
- NetPlanner is **advisory-only** software with a defined build contract
  (`docs/PID.md`). Changes that touch the agents, TCO math, or pricing logic
  must preserve that contract — read the PID first.

## Development setup

Full, reproducible setup, the quality gate, and the build journal live in
[`docs/RUNBOOK.md`](docs/RUNBOOK.md). The short version:

**Backend** (Python 3.12, managed by [uv](https://docs.astral.sh/uv/)):

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload      # http://localhost:8000
```

**Frontend** (Node 20+):

```bash
cd frontend
npm install
npm run dev                               # http://localhost:5173
```

Copy `.env.example` to `.env` and add an `ANTHROPIC_API_KEY` to exercise the AI
features. The rest of the app runs without one.

## The quality gate

Every change must pass the same gate CI enforces. Run it locally before opening
a PR.

**Backend** (from `backend/`):

```bash
uv run ruff check app tests alembic
uv run black --check app tests alembic
uv run isort --check-only app tests alembic
uv run mypy app --ignore-missing-imports
uv run bandit -r app alembic -ll
uv run alembic upgrade head && uv run alembic check
uv run pytest --cov=app --cov-fail-under=80
```

**Frontend** (from `frontend/`):

```bash
npm run lint
npm run build
```

Requirements:

- **Tests pass and coverage stays ≥ 80%.** New behavior needs new tests;
  prefer writing the test first.
- **Types check** (`mypy` clean) and the code is formatted (`black` / `isort`)
  and lint-clean (`ruff` / `eslint`).
- **Schema/ORM changes ship with an Alembic migration** — `alembic check` must
  report no drift.
- **The seven PID eval cases still pass.** Eval 4 (no assumed financial
  inputs) and eval 5 (no unverified pricing presented as confirmed) are
  zero-tolerance — re-run the TCO/pricing tests if you touch those paths.

## Security expectations

NetPlanner follows a secure-by-default standard. Contributions are expected to
uphold it:

- Authentication on every non-public route; ownership checks on every data
  operation (cross-user access returns 404).
- Parameterized queries only; validate all input server-side.
- No secrets in code, logs, or prompts; read them from the environment.
- Treat all retrieved / tool-returned / user-supplied content reaching an LLM
  as untrusted (boundary markers, schema-validated tool output).

`bandit`, `pip-audit`, `npm audit`, Semgrep, and TruffleHog run in CI and block
merges on critical/high findings.

## Commit & PR conventions

- **Conventional commit** subject lines: `feat:`, `fix:`, `refactor:`,
  `docs:`, `test:`, `chore:`, `perf:`, `ci:`.
- Keep PRs focused; describe **what** changed and **why**, and include a test
  plan. The PR template prompts for this.
- Reference the issue you're addressing (`Closes #123`).
- Append a build-journal entry to `docs/RUNBOOK.md` for non-trivial changes,
  as the existing entries do.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
