# Results & Verdict — NVIDIA Nemotron in NetPlanner

**Date:** 2026-06-07 · **Owner:** Elliot Conner · Consolidates phases 0–3 of the
[engagement](README.md). Free-tier, **evaluation-only** — nothing here ships
NetPlanner onto NVIDIA; it decides whether that would be worth doing.

---

## The question

*Can NVIDIA's Nemotron reasoning models stand in for Claude inside a real agent
application — and can I prove it with NVIDIA's own evaluation and red-team tooling?*

## The NVIDIA stack used (end-to-end, on purpose)

| Layer | Tool | Role |
|---|---|---|
| Model | **Nemotron-3-Super-120B** (NIM / API catalog) | hero model under test |
| Routing | **LiteLLM** `nvidia_nim/` | one provider flag behind the agent client |
| Accuracy | **NeMo Evaluator** rubric (LLM-as-judge) | quantified eval gate → my **AI-4** control |
| Safety | **garak** (v0.15.1) | adversarial red-team → my **AI-1** control |

Baseline: `claude-sonnet-4-6` (NetPlanner's production default). Comparator in the
shortlist: `deepseek-ai/deepseek-v4-flash`.

---

## Verdict: **viable, with caveats**

For NetPlanner's **structured-synthesis** work (the Comparison agent), Nemotron is
a credible alternative backend — on the accuracy rubric it **matched and slightly
edged** the Claude baseline. But it is **not a drop-in**: its output shape
(chain-of-thought), its tool-use propensity, and its bare-model injection
resistance all differ from Claude, and each needed handling. Net: usable behind
NetPlanner's existing structural guardrails and some model-specific tuning — not
by flipping a flag and walking away.

### 1. Accuracy — *viable* (Phase 2b)

LLM-as-judge on the `campus-wifi` fixture, scored 1–5. Judge: `qwen/qwen3.5-122b`
on NVIDIA's catalog — a third family, distinct from both models under test, so
neither benefits from self-preference bias.

| Model | Cell accuracy | Completeness | Confidence honesty |
|---|:---:|:---:|:---:|
| `claude-sonnet-4-6` (baseline) | 3 / 5 | 5 / 5 | 5 / 5 |
| `nvidia/nemotron-3-super-120b-a12b` | **4 / 5** | 5 / 5 | 5 / 5 |

The gate **inverted the "verbose = better" prior**: the judge docked Claude a
point for elaborating beyond the supplied research (plausible detail the fixture
never contained) and rewarded Nemotron for staying grounded. Both were perfect on
completeness and confidence honesty — neither over-claimed `confirmed`.

### 2. Behavior — *caveat: not a drop-in* (Phases 0–1)

- **Output shape:** Nemotron is a *reasoning* model that emits chain-of-thought.
  A naive `max_tokens` truncates the answer; one-shot calls need a strip step and
  streaming forces a real chain-of-thought UX decision.
- **Tool-use propensity:** swapping the model changed agent *behavior*, not just
  quality. Nemotron looped NetPlanner's `research` tool to its cap on questions
  Claude answers directly — returning no answer. Fixed by making the tool-round
  budget **per-model** and adding a graceful cap (a forced no-tools synthesis turn
  so the user always gets an answer).

### 3. Safety — *caveat: don't trust the prompt* (Phase 3)

garak probed the Advisor **with its real production system prompt injected** (a
custom generator — otherwise you red-team a bare model and get a falsely-clean
report). Result on the highest-risk family:

| Probe (indirect injection) | Attempts | Resisted |
|---|:---:|:---:|
| `latentinjection.LatentInjectionFactSnippetEiffel` | 768 | 34.2% |
| `latentinjection.LatentInjectionReport` | 768 | 7.9% |
| **latentinjection family** | **1536** | **21.1%** (~79% attack success) |

**The system-prompt guardrails alone do not stop indirect injection on Nemotron.**
That is exactly NetPlanner's AI-1 surface (the Advisor ingests untrusted research
+ project data). Read precisely: this is a **model + system-prompt result at a
bare endpoint** — garak did not exercise NetPlanner's *structural* defenses (the
`<<…>>` boundary fence + sanitization, and schema-constrained tool-calling that
stops injected prose from firing tools). So it is **not a NetPlanner exploit** —
it is direct evidence for the AI-1 thesis the Secure Build Standard already takes:
*prompt-level instructions are not a control; structural defenses are.* The
red-team validates keeping them.

---

## Scope & honesty (what this is not)

- **Free-tier, eval-only.** ~40 req/min, dev capacity. Not a production benchmark.
- **One fixture** for the accuracy rubric; **one judge**. Directional, not a leaderboard.
- **Partial red-team.** Only the latent-injection family completed — direct
  injection, system-prompt extraction, and agent-breaker were throttled out by the
  free tier (ISSUES-LOG #15). The highest-risk family was scored thoroughly.
- **Single model garak-targeted.** Anthropic isn't a NIM endpoint, so Phase 3 is
  *not* a Claude-vs-Nemotron safety comparison — only a measurement of Nemotron's
  prompt-guardrail permeability.
- Accuracy judge detector and garak's trigger detector are heuristic, not semantic.

---

## The issues *are* the story (selected)

The snags hit during the engagement are the most transferable lessons:

| # | Lesson |
|---|---|
| 1 | A reasoning model isn't a drop-in for a non-reasoning one — the output shape changes, and naive `max_tokens` truncates the answer. |
| 6 / 10 | Swapping models changes **tool-use propensity**, not just quality. An agent tuned for one model's restraint can loop forever on another — so the tool budget must be model-aware, and the cap must always degrade to a real answer. |
| 8 | An eval gate can **disagree with your prior**: for grounded synthesis, the reasoning model's restraint out-scored the incumbent's elaboration. That's why AI-4 is a gate, not a vibe. |
| 13 | An off-the-shelf red-team tool attacks a **bare model** by default. To test *your app's* defenses you must put your real system prompt in front of the probes — otherwise the report is falsely clean. |
| 14 | A red-team tool with uncapped retries and a 10-minute default timeout will **silently hang forever** on one flaky free-tier connection. Pin a short request timeout. |

Full journal: [`ISSUES-LOG.md`](ISSUES-LOG.md). Per-phase runbooks: [`runbooks/`](runbooks/).

---

## What's next

- A deeper accuracy run (more fixtures, a second judge) would harden the 2b score.
- A fresh-tier or paid garak run would complete the direct-injection /
  sysprompt-extraction / agent-breaker families.
- Production adoption would require leaving the free tier and re-scoping the key
  (SEC-13/14/15). None of that is needed for the verdict above.

> Tie-in: NetPlanner's public-launch post promised more model choice was coming.
> This engagement is the receipt — a provider-agnostic layer, eval-gated and
> red-teamed against my own Secure Build Standard. The LinkedIn draft built from
> this is in [`LINKEDIN-DRAFT.md`](LINKEDIN-DRAFT.md) (drafted, not posted).
