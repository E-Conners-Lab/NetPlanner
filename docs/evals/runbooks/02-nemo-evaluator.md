# Runbook 02 — Accuracy Eval with NeMo Evaluator

**Phase:** 2 · **Goal:** quantify Nemotron vs Claude on the Comparison agent with
an LLM-as-judge, using NVIDIA NeMo Evaluator.
**Status:** ⬜ not started

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

## Results

| Model | Cell accuracy | Completeness | Confidence honesty | Notes |
|---|---|---|---|---|
| `claude-sonnet-4-6` (baseline) | _/5_ | _/5_ | _/5_ | control |
| Nemotron (hero) | _/5_ | _/5_ | _/5_ | |
| Comparator A | _/5_ | _/5_ | _/5_ | |

## Verification

- [ ] Every shortlisted model scored on the **same** fixtures + rubric.
- [ ] Judge model recorded, and is distinct from models under test.
- [ ] Results table populated; raw judge outputs saved alongside.

## Issues encountered

_Log to `../ISSUES-LOG.md` — microservice setup, NaN scores, rate limits, judge
disagreement, etc._

## Rollback

Eval is read-only on saved pairs; nothing to roll back. Tear down the Evaluator
microservice when done.
