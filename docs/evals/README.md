# NetPlanner × NVIDIA — Reasoning Eval Engagement

**Question this answers:** *Can NVIDIA's Nemotron reasoning models stand in for
Claude inside a real agent application — and can I prove it with NVIDIA's own
evaluation and red-team tooling?*

This is a **living engagement log**, modelled on [`docs/RUNBOOK.md`](../RUNBOOK.md):
it exists so anyone can reproduce the evaluation from a clean machine, and so the
process — including every issue hit and how it was resolved — is captured as it
happens. The issue journal is deliberate: it is the raw material for the public
writeup.

> Free-tier scope. The NVIDIA API catalog free tier (~40 req/min, no card) is for
> **development and evaluation, not production**. Nothing here ships NetPlanner
> onto NVIDIA — it decides whether that would be worth doing.

---

## Why this is framed around the NVIDIA ecosystem

Anyone can call an OpenAI-compatible endpoint. This engagement deliberately uses
NVIDIA's *own* stack end-to-end so the work demonstrates ecosystem fluency, not
just API consumption:

| Layer | NVIDIA tool | What it shows |
|---|---|---|
| Models | **Nemotron** reasoning family (via NIM / API catalog) | Hero model, not a hosted third party |
| Routing | **LiteLLM** `nvidia_nim/` provider | Multi-provider AI engineering |
| Accuracy | **NeMo Evaluator** (LLM-as-judge) | Quantified eval gate — maps to my AI-4 control |
| Safety | **garak** (Agent-breaker, system-prompt-extraction probes) | Adversarial red-team — maps to my AI-1 control |

The through-line: *I red-teamed and eval-gated my own production agents with
NVIDIA's stack, against my own published Secure Build Standard.*

---

## Phase plan

Documentation grows **with** execution — each runbook is filled with real
commands and real issues as that phase runs, not pre-written.

| Phase | Runbook | Deliverable | Status |
|---|---|---|---|
| 0 · Setup | [`runbooks/00-nvidia-setup.md`](runbooks/00-nvidia-setup.md) | Scoped NVIDIA key + Nemotron-first model shortlist | ✅ done (2026-06-05) |
| 1 · Provider layer | [`runbooks/01-litellm-provider-layer.md`](runbooks/01-litellm-provider-layer.md) | LiteLLM abstraction behind the agent client | ✅ done — Comparison + Advisor ported (2026-06-05) |
| 2 · Accuracy eval | [`runbooks/02-nemo-evaluator.md`](runbooks/02-nemo-evaluator.md) | NeMo Evaluator scores: Nemotron vs Claude baseline | ⬜ not started |
| 3 · Red-team | [`runbooks/03-garak-redteam.md`](runbooks/03-garak-redteam.md) | garak report on the Advisor agent | ⬜ not started |
| 4 · Writeup | [`runbooks/04-results-and-writeup.md`](runbooks/04-results-and-writeup.md) | Results tables + LinkedIn draft | ⬜ not started |
| 5 · OpenRouter (optional) | [`runbooks/05-openrouter-byo-provider.md`](runbooks/05-openrouter-byo-provider.md) | OpenRouter spike for production BYO-provider — separate angle, not required for the core verdict | ⬜ stub |

Full goals, scope, success criteria, and the identity/secrets table are in
[`SPEC.md`](SPEC.md). The running lab notebook is [`ISSUES-LOG.md`](ISSUES-LOG.md).

---

## How to use these docs

1. Read [`SPEC.md`](SPEC.md) — it is the contract for the engagement.
2. Execute one phase at a time, in order. Each runbook is self-contained.
3. As you go, append every non-trivial snag to [`ISSUES-LOG.md`](ISSUES-LOG.md)
   with a one-line "why it's interesting" — that flag is what makes the post.
4. Update the phase status table above when a phase completes.
