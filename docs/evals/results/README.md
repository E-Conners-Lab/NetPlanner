# Eval Results

Outputs from `backend/scripts/eval_compare.py`, one JSON per (fixture, provider).
Research data is supplied from `../fixtures/`, so each matrix reflects the
**model's reasoning alone** (no live web search) — making Claude vs Nemotron an
apples-to-apples comparison.

Reproduce (from `backend/`):

```bash
uv run python scripts/eval_compare.py                 # both providers (2a)
uv run python scripts/eval_compare.py --fixture campus-wifi
uv run python scripts/eval_judge.py                   # LLM-as-judge scores (2b)
```

File naming: `<fixture>__<provider>.json` are the raw Comparison outputs;
`<fixture>__<provider>__judge.json` are the Phase 2b LLM-as-judge verdicts.

## Phase 2a — `campus-wifi` (2026-06-05)

First **live** run of the Comparison agent on NVIDIA Nemotron through the
provider layer (not a mock).

| | `claude-sonnet-4-6` (baseline) | `nvidia/nemotron-3-super-120b-a12b` |
|---|---|---|
| Matrix completeness | 3×4, full | 3×4, full |
| Confidence tagging | all `estimated` (honest) | all `estimated` (honest) |
| Style | verbose, adds domain knowledge, heavily hedged | concise, grounded in supplied research, propagates source URLs |
| Failure modes seen | none | none |

Qualitatively, Nemotron held up well on this structured-synthesis task. The
numeric LLM-as-judge scoring is Phase 2b, below.

Raw outputs: `campus-wifi__anthropic.json`, `campus-wifi__nvidia_nim.json`.

## Phase 2b — LLM-as-judge scorecard (2026-06-05)

The 2a qualitative read, scored. NeMo Evaluator's microservice was disproportionate
for two saved pairs, so we ran the spec's blessed fallback (SPEC §8): the
**identical rubric** via `scripts/eval_judge.py`, judged by `qwen/qwen3.5-122b-a10b`
— a third family, distinct from both models under test (no self-preference bias).
See [`../runbooks/02-nemo-evaluator.md`](../runbooks/02-nemo-evaluator.md).

| Model | Cell accuracy | Completeness | Confidence honesty |
|---|---|---|---|
| `claude-sonnet-4-6` (baseline) | 3/5 | 5/5 | 5/5 |
| `nvidia/nemotron-3-super-120b-a12b` (hero) | **4/5** | 5/5 | 5/5 |

**The result inverted the "verbose = better" prior.** The judge docked Claude an
accuracy point for *inventing* AI/assurance detail the research input never
supplied, and rewarded Nemotron for staying grounded. Both were perfect on
completeness and confidence honesty — neither over-claimed `confirmed`. For this
grounded-synthesis task the eval gate says **Nemotron is viable, and marginally
more faithful than the incumbent**.

Raw verdicts (with per-criterion judge rationales):
`campus-wifi__anthropic__judge.json`, `campus-wifi__nvidia_nim__judge.json`.

## Phase 2a — the live app on Nemotron (screenshots)

The full NetPlanner app run with `provider=nvidia_nim` — the **Advisor streaming a
real business-decision answer from Nemotron**, captured via Playwright
(`../scripts/capture_screenshots.py`).

![NetPlanner AI Advisor answering on Nemotron](../images/nemotron-advisor.png)

Images in `../images/`:
- `nemotron-advisor.png` — full Advisor answer (the hero shot; crop as needed)
- `nemotron-advisor-hero.png` — viewport crop
- `nemotron-advisor-empty.png` — Advisor empty state
- `nemotron-dashboard.png` — project view

**Finding #6 (the standout):** the first live Advisor run on Nemotron returned
*no answer* — Nemotron chose to call the `research` tool four rounds straight
(hitting the tool-loop cap) on a framing/ROI question that Claude answers
directly. Same question + "do not look anything up" → a clean, single-round
10k-char advisory answer. **Tool-use propensity is model-dependent** — an agent's
tool-loop budget and guardrails tuned for one model can loop forever on another.
The demo question is phrased to stay single-round; see [`../ISSUES-LOG.md`](../ISSUES-LOG.md).
