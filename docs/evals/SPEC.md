# Eval Engagement Spec — NVIDIA Reasoning Models in NetPlanner

**Version:** 0.1 (draft) · **Date:** 2026-06-05 · **Owner:** Elliot Conner

This is the contract for the engagement. If work drifts from this, update the
spec first.

---

## 1. Goal

Produce a **defensible, reproducible answer** to: *would NVIDIA Nemotron models
be a viable alternative LLM backend for NetPlanner's agents?* — with evidence from
NVIDIA's own accuracy (NeMo Evaluator) and safety (garak) tooling, documented
well enough to publish.

## 2. Non-goals

- **Not** migrating NetPlanner's production path off Anthropic. Claude stays the
  default; NVIDIA is added behind a flag for evaluation only.
- **Not** replacing the Research agent's hosted web search (Anthropic-proprietary;
  see scope below).
- **Not** a production deployment. Free tier is eval-only.

## 3. Scope — which agents

NetPlanner has three LLM agents. Eval coverage is deliberately uneven because the
agents differ in portability:

| Agent | In scope? | Rationale |
|---|---|---|
| **Comparison** (`comparison.py`) | ✅ Primary | Tool-free, JSON-in/JSON-out — cleanest reasoning comparison. The eval's anchor. |
| **Advisor** (`advisor.py`) | ✅ Secondary | Streaming + custom tool loop — tests LiteLLM's translation *and* is the garak red-team target. |
| **Research** (`research.py`) | ❌ Excluded | Depends on Anthropic's `web_search_20250305` hosted tool; no NIM equivalent. Out of scope to keep the comparison honest. |

## 4. Success criteria

The engagement is "done" when all of the following exist and are committed:

- [ ] NVIDIA + Claude run the **same fixtures** through the Comparison agent, with
      a NeMo Evaluator LLM-as-judge score for each (accuracy, completeness,
      pricing-confidence honesty).
- [ ] The Advisor agent runs end-to-end on a Nemotron model via LiteLLM
      (streaming + at least one successful tool-call round).
- [ ] A garak report exists for the Advisor on at least the prompt-injection and
      system-prompt-extraction probe families, with results summarized.
- [ ] A results table comparing models, plus an issues log with ≥1 genuine snag
      per phase.
- [ ] A LinkedIn draft built from the above.

**Decision output:** a one-paragraph verdict — *viable / viable-with-caveats /
not-yet* — with the numbers that support it.

## 5. Eval methodology

### Accuracy (NeMo Evaluator — maps to AI-4)
- **Type:** custom LLM-as-a-judge over pre-generated prompt/response pairs (the
  `data` task type — no live inference needed at judge time).
- **Judge model:** a strong model via OpenAI-compatible endpoint (judge ≠ model
  under test, to avoid self-preference bias). Record which judge and why.
- **Metrics:** per-criterion 1–5 scores for (a) matrix cell accuracy vs research
  input, (b) completeness (no silently dropped vendor×criterion cells),
  (c) confidence-tag honesty (does it over-claim `confirmed`?).
- **Baseline:** current Claude output on identical fixtures = the control.

### Safety / robustness (garak — maps to AI-1)
- **Target:** the Advisor agent's model endpoint via LiteLLM.
- **Probe families (confirm exact module names with `garak --list_probes`):**
  prompt injection, system-prompt extraction, and the v0.15+ Agent-breaker probe
  (tests tools exposed to the agent — directly relevant to the `research` tool).
- **Pass bar:** document the hit-rate per probe; flag anything that defeats the
  Advisor's role guardrails or leaks the system prompt.

## 6. Identity & secrets table

Per the Secure Build Standard (least privilege; define identities before writing
automation):

| Identity | System | Needs | Must NOT have |
|---|---|---|---|
| `nvidia-eval-key` (`nvapi-…`) | NVIDIA API catalog / NIM | Inference on shortlisted chat models, free tier | Production routing, paid tier, write access to repo secrets |
| `anthropic-key` (existing) | Anthropic | Baseline generation only | — (already scoped) |
| judge-endpoint key | judge provider | Inference for LLM-as-judge | Anything beyond eval runs |

Rules: keys live in `.env` (already git-ignored), **never** in fixtures, runbook
examples, screenshots, or the published post (SEC-12/18). Free-tier NVIDIA key is
dev-only and must never be reused for any production path (SEC-13). Scope each key
to the minimum and rotate after the engagement (SEC-14/15).

## 7. Security mapping (the showcase angle)

| My standard | How this engagement exercises it |
|---|---|
| **AI-1** (prompt injection) | garak Agent-breaker + system-prompt-extraction against the Advisor |
| **AI-4** (eval gate before model change) | NeMo Evaluator scores gate the "is Nemotron viable" decision |
| **AI-3** (context hygiene) | Confirm no secrets/PII reach the new provider's context |
| **SEC-13/14/15** | Scoped, dev-only, rotated NVIDIA key |

## 8. Risks & known frictions

- **NeMo Evaluator is a deployable microservice**, not a one-liner — standing it
  up (Docker/compose) is itself a documented phase-2 step and a likely source of
  "issues I ran into." If setup proves too heavy for the free context, fall back
  to the same LLM-as-judge rubric run via a thin script and note the trade-off.
- **40 req/min** throttles batch evals — fixture sets stay small and runs are
  rate-limit-aware.
- **Exact Nemotron model IDs change** in the catalog — never hardcode; pull the
  current ID from build.nvidia.com at phase 0.
- **LiteLLM translation gaps** — Anthropic-specific params need `drop_params`;
  streaming/tool-call edge cases are expected and are good journal entries.
- **Data sensitivity** — use synthetic vendor/pricing fixtures only; no real
  customer infrastructure data through a free dev tier.
