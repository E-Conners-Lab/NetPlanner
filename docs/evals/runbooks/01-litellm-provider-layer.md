# Runbook 01 — LiteLLM Provider Layer

**Phase:** 1 · **Goal:** route NetPlanner's agents to Anthropic **or** NVIDIA NIM
through one abstraction, without breaking the Claude default.
**Status:** ✅ done (2026-06-05) — provider layer + Comparison (1a) + Advisor
streaming/tool port (1b). Live `provider=nvidia_nim` runs happen in Phase 2.

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

- [x] `provider=anthropic` → full suite passes unchanged, 228 passed / 1 skipped
      (no behavior drift; production path byte-for-byte the same).
- [x] Provider layer in place: `app/agents/llm.py` `complete()` dispatches on the
      `provider` setting; Comparison agent now calls it instead of the SDK.
- [x] NVIDIA path unit-tested (LiteLLM `nvidia_nim/` model id, scoped key,
      `drop_params`, thinking-strip) — `llm.py` 100% covered; project total 93%.
- [x] `litellm==1.87.1` pinned (SEC-30); `pip-audit` clean (SEC-29).
- [x] Advisor ported (1b): `stream_tool_turn()` + `format_tool_results()`
      normalize streaming, tool-call shape, and stop reasons across providers.
      Anthropic path tested through the wrapper; NVIDIA streaming/tool path tested
      (fragment accumulation, content-filter→refusal, plain-text end). `llm.py`
      99%, `advisor.py` 96%, 235 tests green.
- [ ] **Live** `provider=nvidia_nim` runs (Comparison matrix + Advisor tool round)
      on real fixtures — Phase 2, where fixtures are built. Revisit the streaming
      chain-of-thought gap (Finding #3) there.

## What landed (2026-06-05)

- `config.py`: `provider` flag (default `anthropic`), `nvidia_api_key`,
  `nvidia_model`, `require_nvidia_api_key()` fail-fast accessor.
- `app/agents/llm.py`:
  - `complete()` + `LLMResult` (one-shot, Comparison) — native Anthropic preserves
    `effort` + refusal; NVIDIA via LiteLLM strips reasoning CoT (Finding #1).
  - `stream_tool_turn()` + `ToolCall`/`TurnResult` + `format_tool_results()`
    (streaming + tools, Advisor) — normalizes tool schema (`input_schema` vs
    `function.parameters`), stream events, streamed tool-call fragments, and stop
    reasons. Neutral tool spec (`NeutralTool`) translated per provider.
- `comparison.py`: provider-agnostic via `complete()`. `advisor.py`:
  provider-agnostic via `stream_tool_turn()`; tool execution + refusal policy stay
  in the agent. No route or schema changes.
- Refusal logging for one-shot moved into the wrapper; Advisor keeps its own
  refusal→`AdvisorRefusalError` policy, fed by `TurnResult`. **Research** stays on
  the native path (Anthropic-proprietary web search — out of eval scope).

## Issues encountered

_Expected hot spots — log specifics to `../ISSUES-LOG.md`:_
- Anthropic-only params (`system` handling, tool schema) rejected by NIM →
  `drop_params`.
- Streaming delta shape differences surfaced through LiteLLM.
- Tool-call argument formatting (Anthropic `input` vs OpenAI `arguments`).

## Rollback

Set `provider=anthropic` (default) — the NVIDIA path is dormant. Revert the
branch if the wrapper regresses the Claude path.
