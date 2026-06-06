# Runbook 03 — Red-Team with garak

**Phase:** 3 · **Goal:** adversarially probe the Advisor agent's model with
NVIDIA garak — prompt injection, system-prompt extraction, and the Agent-breaker
probe.
**Status:** ⬜ not started

---

## Objective

Test whether the Advisor's role guardrails and hardcoded system prompt survive
known attacks, on the Nemotron endpoint. This is the AI-1 (prompt-injection)
control, made concrete — and the most "demo-able" part of the writeup.

## Prerequisites

- Runbook 00 complete (`NVIDIA_API_KEY`).
- Python **3.10–3.12** (garak requirement).
- The Advisor's system prompt available to inject as the model's system message,
  so the probes attack the *real* guardrails, not a bare model.

## Steps

1. **Install** (isolated env):
   ```bash
   python -m pip install -U garak
   garak --list_probes          # confirm exact probe module names for your version
   ```
2. **Pick the target.** garak speaks NIM and LiteLLM natively. Either:
   - `--model_type nim --model_name <MODEL_ID>` (direct NIM), or
   - point garak at the LiteLLM layer for parity with how NetPlanner calls it.
   Record which, and why.
3. **Select probes** (confirm names from step 1 — module names vary by version):
   - prompt injection family
   - system-prompt extraction (v0.15+)
   - **Agent-breaker** (v0.15+) — tests tools exposed to the agent; maps to the
     Advisor's `research` tool.
4. **Run**, supplying the Advisor system prompt as context so guardrails are in
   play. garak sends each prompt ~10× by default (LLM output is non-deterministic)
   — budget for the 40 req/min limit.
   ```bash
   garak --model_type nim --model_name <MODEL_ID> \
         --probes <injection_probe>,<sysprompt_probe>,<agent_breaker_probe>
   ```
5. **Read the report** (garak emits a JSONL/HTML report with per-probe hit-rates).

## Results

| Probe family | Attempts | Hits | Hit-rate | Defeated a guardrail? |
|---|---|---|---|---|
| Prompt injection | | | | |
| System-prompt extraction | | | | |
| Agent-breaker (tool misuse) | | | | |

## Verification

- [ ] At least the three probe families above ran to completion.
- [ ] Report saved under `docs/evals/` (redact any leaked prompt content per
      SEC-12/18 before committing).
- [ ] Results table summarized; notable single failures captured verbatim (with
      secrets/PII stripped) for the writeup.

## Issues encountered

_Log to `../ISSUES-LOG.md` — probe-name drift, rate-limit throttling on 10×
repetition, detector false positives, NIM vs LiteLLM target differences._

## Rollback

Read-only against the endpoint; nothing to roll back. Uninstall garak's venv when
done.
