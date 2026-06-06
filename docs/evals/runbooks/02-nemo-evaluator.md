# Runbook 02 — Accuracy Eval with NeMo Evaluator

**Phase:** 2 · **Goal:** quantify Nemotron vs Claude on the Comparison agent with
an LLM-as-judge, using NVIDIA NeMo Evaluator.
**Status:** ✅ done (2026-06-05) — ran via the spec's thin-script fallback (see
"What we actually ran" below); microservice deferred as too heavy for this context.

---

## Objective

Score model outputs on the same fixtures with a consistent rubric, so the
"viable / not-yet" decision rests on numbers, not vibes. This is the AI-4
eval-gate control, made concrete.

## Prerequisites

- Runbook 01 complete (Comparison agent runs on both providers).
- A small **synthetic** fixture set: research-input payloads + expected coverage.
  No real customer data (SPEC §8).

## Approach

NeMo Evaluator's **LLM-as-a-judge** supports the `data` task type — judge
pre-generated prompt/response pairs directly, no live inference at judge time.
That fits perfectly: generate Comparison outputs once per model, then judge the
saved pairs.

> **Deployment note / likely friction:** NeMo Evaluator is a deployable
> microservice, not a pip one-liner. Stand it up per the NeMo Microservices docs
> (Docker/compose). If the free-context setup proves too heavy, fall back to the
> **same rubric** run via a thin LLM-as-judge script against an OpenAI-compatible
> judge endpoint, and document the trade-off in the issues log. Either way the
> rubric and fixtures are identical, so results stay comparable.

## Steps

1. **Generate** Comparison outputs for each shortlisted model on the fixtures;
   save as `{model}__{fixture}.json` pairs.
2. **Configure the judge** (OpenAI-compatible endpoint; judge ≠ model-under-test
   to avoid self-preference). Example judge model block:
   ```json
   {"model": {"url": "https://integrate.api.nvidia.com/v1",
              "name": "<judge-model-id>",
              "format": "openai",
              "api_key_secret": "judge-api-key"}}
   ```
   Use low temperature for stable scoring; request structured output to cut NaN
   rates (NVIDIA's guidance for <70B judges).
3. **Define the rubric** — three 1–5 metrics:
   - **Cell accuracy** — do matrix cells match the research input?
   - **Completeness** — any silently dropped vendor×criterion cells?
   - **Confidence honesty** — does it over-claim `confirmed` vs `estimated`?
4. **Run** the eval job (NeMo Evaluator API/SDK, or the fallback script).
5. **Collect** per-model scores into the results table below.

## What we actually ran

NeMo Evaluator is a deployable microservice (Helm/Docker), and for a `data`-task
judge job the inference happens on a remote endpoint anyway — so standing the
full platform up on a laptop was disproportionate to the payoff here. Per SPEC §8
and the deployment note above, we took the **fallback**: a thin LLM-as-judge
script (`backend/scripts/eval_judge.py` + `app/evals/judge.py`) that applies the
**identical rubric** against the same saved pairs. The rubric and fixtures are
unchanged, so these scores would line up with a microservice run. Microservice
stand-up is deferred, not abandoned (see ISSUES-LOG #7).

```bash
# from backend/ (needs NVIDIA_API_KEY in backend/.env)
uv run python scripts/eval_judge.py            # scores every saved results/ pair
```

- **Judge model:** `qwen/qwen3.5-122b-a10b` via NVIDIA's OpenAI-compatible
  endpoint (LiteLLM `nvidia_nim/`). Chosen because it is a **third family** —
  distinct from both models under test (Claude and Nemotron), so neither benefits
  from self-preference bias. A `assert_judge_independent()` guard hard-fails if
  the judge id ever matches a model under test.
- **Settings:** `temperature=0` for reproducible scoring; structured JSON output
  requested (NVIDIA's <70B guidance) and parsed defensively; reasoning `<think>`
  stripped before parsing; out-of-range / missing scores raise rather than
  silently becoming NaN. The judge gets generous `max_tokens` (2048) plus a
  small retry, because a reasoning judge spends tokens on its `<think>` block
  before the JSON and a tight cap truncates the answer (ISSUES-LOG #9).

## Results

Judge: `qwen/qwen3.5-122b-a10b` · fixture: `campus-wifi` · 2026-06-05 ·
raw verdicts: `../results/campus-wifi__*__judge.json`

| Model | Cell accuracy | Completeness | Confidence honesty | Notes |
|---|---|---|---|---|
| `claude-sonnet-4-6` (baseline) | 3/5 | 5/5 | 5/5 | control; lost accuracy points for **inventing** AI/assurance detail not in the research |
| `nvidia/nemotron-3-super-120b-a12b` (hero) | 4/5 | 5/5 | 5/5 | **out-scored the baseline on accuracy** by staying grounded in the supplied research |
| Comparator (deepseek-v4-flash) | — | — | — | not generated this round (scope: Claude vs Nemotron) |

**Headline:** the eval gate **inverted the "verbose = better" prior.** The judge
docked Claude a full accuracy point for elaborating beyond the research input
(plausible domain knowledge the fixture never supplied), and rewarded Nemotron
for grounding. Nemotron's one lost point: it marked some AI/assurance cells "Not
available" where the judge felt the research implied a tiered feature existed.
Both models were flawless on completeness and confidence honesty (no over-claimed
`confirmed` tags). This numerically confirms the Phase 2a qualitative read.

## Verification

- [x] Every scored model ran on the **same** fixture + rubric.
- [x] Judge model recorded (`qwen/qwen3.5-122b-a10b`), and is distinct from both
      models under test (enforced by `assert_judge_independent`).
- [x] Results table populated; raw judge outputs saved alongside under
      `../results/*__judge.json`.

## Issues encountered

Logged to `../ISSUES-LOG.md`: #7 (microservice → thin-script fallback trade-off)
and the headline judge finding (accuracy ranking inverted the verbose-is-better
prior). The 40-rpm free-tier limit was a non-issue at two judge calls.

## Rollback

Eval is read-only on saved pairs; nothing to roll back. The thin-script path
stands up no microservice. (If the NeMo Evaluator microservice is later deployed
for the full-stack showcase, tear it down when done.)
