# Runbook 01 — LiteLLM Provider Layer

**Phase:** 1 · **Goal:** route NetPlanner's agents to Anthropic **or** NVIDIA NIM
through one abstraction, without breaking the Claude default.
**Status:** ⬜ not started

---

## Objective

Introduce LiteLLM behind the existing `get_anthropic_client()` factory so an
agent can target Claude (default) or a Nemotron model (eval) via a config flag.
LiteLLM normalizes the three coupling points the native Anthropic path bakes in:
tool-call format, streaming event shape, and stop-reason enums.

## Prerequisites

- Runbook 00 complete (`NVIDIA_API_KEY` in `.env`, shortlist IDs known).
- Backend test suite green on `main` before touching anything.

## Design (keep the Claude path untouched)

- Add a `provider` setting (`anthropic` | `nvidia_nim`) in
  `backend/app/config.py`, defaulting to `anthropic`.
- Add a provider-agnostic client module (e.g. `backend/app/agents/llm.py`) that
  wraps LiteLLM. `nvidia_nim/<model>` auto-routes to
  `https://integrate.api.nvidia.com/v1`.
- Anthropic-specific params that NIM rejects → rely on LiteLLM `drop_params`.
- **Comparison agent first** (tool-free) — lowest-risk port. Advisor (streaming +
  tool loop) second, since it exercises LiteLLM's translation hardest.
- Gate everything behind the flag so `main`'s production behavior is identical
  when `provider=anthropic`.

## Steps

1. Pin the dependency (exact version — SEC-30) in `backend/pyproject.toml`:
   ```bash
   # confirm latest stable, then pin ==
   uv add 'litellm==<pinned>'
   ```
2. Add the `provider` + model settings to `config.py` (env-overridable).
3. Write `llm.py` — a thin wrapper exposing the calls the agents need
   (completion + streaming). Map the NetPlanner model setting → LiteLLM model
   string (`nvidia_nim/<id>` when provider is NVIDIA).
4. Wire the **Comparison agent** to call through the wrapper. Run its tests.
5. Wire the **Advisor agent**; verify streaming and one tool-call round.
6. Add/adjust unit tests that mock the wrapper for both providers.

## Verification

- [ ] `provider=anthropic` → existing tests pass unchanged (no behavior drift).
- [ ] `provider=nvidia_nim` → Comparison agent returns a valid matrix on a fixture.
- [ ] Advisor streams tokens and completes ≥1 tool-call round on Nemotron.
- [ ] Coverage stays ≥ 80% (testing standard).

## Issues encountered

_Expected hot spots — log specifics to `../ISSUES-LOG.md`:_
- Anthropic-only params (`system` handling, tool schema) rejected by NIM →
  `drop_params`.
- Streaming delta shape differences surfaced through LiteLLM.
- Tool-call argument formatting (Anthropic `input` vs OpenAI `arguments`).

## Rollback

Set `provider=anthropic` (default) — the NVIDIA path is dormant. Revert the
branch if the wrapper regresses the Claude path.
