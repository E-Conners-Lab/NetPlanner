## Summary
What does this PR change, and why?

Closes #<!-- issue number, if any -->

## Changes
-

## Test plan
Run the quality gate (see [CONTRIBUTING.md](../CONTRIBUTING.md)):

- [ ] `ruff` / `black` / `isort` / `mypy` / `bandit -ll` clean (backend)
- [ ] `alembic upgrade head && alembic check` — parity OK (if schema changed)
- [ ] `pytest --cov-fail-under=80` passes
- [ ] `npm run lint` + `npm run build` clean (frontend)
- [ ] The 7 PID eval cases still pass (if TCO/pricing/agents touched)

## Security checklist
- [ ] Auth on every new non-public route; ownership checked on every data op
- [ ] Input validated server-side; parameterized queries only
- [ ] No secrets in code, logs, or prompts
- [ ] Retrieved / tool / user content reaching an LLM treated as untrusted

## Notes
Anything reviewers should know — deviations, follow-ups, conscious trade-offs.
