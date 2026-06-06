# Issues Log — Lab Notebook

The running journal for the engagement. **Append every non-trivial snag as it
happens**, while the detail is fresh. The "Why it's interesting" column is the
filter for what makes the public writeup — if a snag has a generalizable lesson,
flag it.

Format mirrors `docs/RUNBOOK.md` §7: symptom → cause → fix.

| # | Date | Phase | Symptom | Cause | Fix | Why it's interesting (post-worthy?) |
|---|---|---|---|---|---|---|
| _ex_ | 2026-06-05 | 1 | _e.g. LiteLLM 400 on Anthropic `system` param_ | _NIM rejects Anthropic-specific field_ | _set `drop_params: true`_ | _Concrete example of the Anthropic↔OpenAI translation gap_ |
| 1 | 2026-06-05 | 0 | Nemotron smoke test returned chain-of-thought (`"The user says…"`) instead of `ready`; cut off mid-sentence | `nemotron-3-super-120b` is a **reasoning** model that emits thinking tokens; `max_tokens=16` truncated before the final answer | Give reasoning models generous `max_tokens`; plan a downstream step to strip thinking from the final content | ✅ Yes — "swapping a reasoning model into an app built around a non-reasoning one isn't a drop-in; the output shape changes." Strong post beat. |
| 2 | 2026-06-05 | 0 | `deepseek-ai/deepseek-v4-pro` smoke test hung, `curl` returned HTTP 000 at 30s | Model cold-start / slow inference on the free dev tier (~40 rpm, shared capacity) | Swapped comparator to `deepseek-ai/deepseek-v4-flash` (clean 200); kept `qwen3.5-122b` as backup | ✅ Yes — "free tier ≠ uniform latency; pick models that actually respond, and budget for cold starts." Sets up the not-for-production caveat. |
| 3 | 2026-06-05 | 1b | Non-streaming `<think>`-strip is easy; the **streaming** Advisor can't strip CoT the same way (tags span chunk boundaries) | Reasoning models emit chain-of-thought; the comparison agent buffers + strips, but a streamed turn yields tokens as they arrive | Yield only `delta.content`, skip `delta.reasoning_content` (works for models that separate CoT). Inline `<think>` in streamed `content` is a **known gap** — revisit in Phase 2 (buffer-and-strip, or non-streaming for reasoning models) | ✅ Yes — strong beat: "the provider abstraction that's invisible for one-shot calls *leaks* for streaming. Reasoning models force a real streaming-UX decision." |
| 4 | 2026-06-05 | 2a | First live NVIDIA run failed: `NVIDIA_API_KEY is required` even though the key was in `.env` | The key was added to the **repo-root** `.env` in Phase 0, but the backend reads `backend/.env` (its `env_file` is relative to the backend CWD) | Moved the key into `backend/.env` (where `ANTHROPIC_API_KEY` already lives) | ⚠️ Minor but relatable: "config location bites — 'it's in my .env' isn't enough; it has to be in the .env the process actually reads." |
| 5 | 2026-06-05 | 2a | `python scripts/eval_compare.py` → `ModuleNotFoundError: app` | Plain script runs don't get the backend dir on `sys.path` (pytest's `pythonpath` only applies under pytest) | `sys.path.insert(0, backend_dir)` at the top of the script | Minor tooling gotcha; not post-worthy on its own. |
| 6 | 2026-06-05 | 2a | Live Advisor on Nemotron returned **no answer** — just "(Research budget reached)" — on a framing/ROI question Claude answers directly | Nemotron is **much more eager to call the `research` tool**: it chose to research 4 rounds straight (hitting the tool-loop cap) instead of answering. Same question + "do not look anything up" → clean 1-round answer. Threading is correct; it's a model **tool-use propensity** difference | For the demo, phrase the question to avoid a price lookup. Product follow-up: when the tool budget is hit, the Advisor should emit a partial answer, not just the budget notice | ✅ **Strong finding** — "swapping models isn't just quality; *tool-use propensity* changes. An agent tuned for one model's restraint can loop forever on another. Your tool-loop budget + guardrails are model-dependent." |
| 7 | 2026-06-05 | 2b | NeMo Evaluator is a deployable microservice (Helm/Docker), not a pip install — too heavy to stand up on a laptop just to score 2 saved pairs | The microservice is built for managed, repeatable eval *jobs* at scale; for a `data`-task LLM-as-judge the inference runs on a remote endpoint regardless, so the platform adds ops overhead without changing the scores here | Took the spec's blessed fallback (SPEC §8): a thin LLM-as-judge script (`app/evals/judge.py` + `scripts/eval_judge.py`) running the **identical rubric** against the same pairs. Rubric + fixtures unchanged → scores stay comparable. Microservice deferred, not abandoned | ⚠️ Relatable: "the heaviest tool isn't always the right-sized tool. The rubric *is* the eval — the microservice is just one runner for it. Match infra weight to the job." |
| 8 | 2026-06-05 | 2b | The judge **inverted** the intuitive ranking: it scored Claude's accuracy **3/5** and Nemotron's **4/5** | Claude elaborated beyond the supplied research (plausible AI/assurance detail the fixture never contained); the judge counts un-grounded specifics against `cell_accuracy`. Nemotron stayed grounded and scored higher (its one lost point: marking some AI cells "Not available" where the research arguably implied a tiered feature) | None needed — this is the result. Numerically confirms the 2a qualitative read | ✅ **Strong finding** — "an eval gate disagrees with the 'more verbose, more knowledgeable = better' prior. For a *grounded-synthesis* task, the reasoning model's restraint scored higher than the baseline's domain elaboration. This is exactly why AI-4 is a gate, not a vibe." |
| 9 | 2026-06-05 | 2b | A live re-run **flaked on the Claude pair only**: `JudgeParseError: No JSON object found`. Nemotron scored fine the same run; a third run scored Claude cleanly (3/5/5 again, reproducible) | The judge (Qwen) is a reasoning model — it spends tokens on a `<think>` block before the JSON. The longer/more-verbose Claude matrix pushed the answer past the 1024-token cap, so the reply got truncated before the JSON object. Free-tier sampling is also non-deterministic | Bumped the judge `max_tokens` 1024→2048 (headroom to finish the JSON after reasoning) and added a small retry on `JudgeParseError` (a fresh sample usually lands). The parser already fails loud rather than emitting a NaN | ✅ **Good beat** — "the same reasoning-model gotcha that bit the *agent* (Finding #1) bites the *judge*: chain-of-thought eats your token budget. Reasoning judges need headroom + a retry, and a strict parser so a flake fails loudly instead of poisoning the scorecard." |
| 10 | 2026-06-06 | 2 | **Fix for #6 shipped.** The Advisor hitting its tool-round cap used to yield a dead-end `(Research budget reached for this turn.)` with no answer | The cap was a hard loop bound plus a system-prompt nudge — both model-blind. Nemotron's heavier tool-use propensity (#6) burned every round on `research`, so the cap fired with nothing synthesized | Two changes: (1) **graceful cap** — on budget exhaustion the Advisor runs one final turn with tools force-disabled (`stream_tool_turn(..., allow_tools=False)` → Anthropic `tool_choice:{"type":"none"}` / OpenAI `"none"`), so the model MUST answer from the research already gathered; (2) **per-model tool policy** — the round budget is now per-provider in `config.py` (`advisor_tool_rounds()`: Claude 4, Nemotron 2), since tool-use propensity is model-dependent. Claude's default path is unchanged | ✅ **Closes the loop on #6** — "the fix for a model-specific failure isn't a bigger global limit; it's making the limit *model-aware* and making the fallback *always produce an answer*. Guardrails tuned per model, plus a graceful degrade, beat a one-size loop cap." |

<!-- Append rows below. Keep the example row for format reference. -->

---

## Phase verdicts

Short prose summary captured at the **end of each phase** — what worked, what
surprised you, what you'd do differently. These become the post's section beats.

### Phase 0 — Setup
Signup was frictionless (email only, no card). The OpenAI-compatible endpoint
(`integrate.api.nvidia.com/v1`) and `GET /v1/models` worked first try. Two
findings already worth the post: (1) the hero Nemotron is a **reasoning** model
that emits chain-of-thought — swapping it into an app built around a
non-reasoning model is *not* a drop-in; output shape changes and naive
`max_tokens` truncates the answer. (2) Free-tier latency is **not uniform** —
`deepseek-v4-pro` timed out (HTTP 000 locally, 504 at the gateway) while its
`-flash` sibling answered instantly. Shortlist locked: Nemotron-3-super-120b
(hero) vs deepseek-v4-flash (comparator) vs claude-sonnet-4-6 (baseline).

### Phase 1 — Provider layer
Both LLM agents now run through one `complete()` / `stream_tool_turn()` wrapper
that dispatches on the `provider` flag (default `anthropic`, unchanged). The
Comparison port (1a) was trivial — tool-free, one-shot. The Advisor port (1b)
was where the three coupling points actually bit: tool **schema** (`input_schema`
vs `function.parameters`), **stream event** shape (Anthropic `content_block_delta`
vs OpenAI `choices[].delta`), streamed **tool-call fragments** accumulated by
index, and **stop reasons** (`tool_use`/`refusal` vs `tool_calls`/`content_filter`).
Biggest lesson (Finding #3): the abstraction is clean for one-shot calls but
**streaming + reasoning models** forces a genuine UX decision about chain-of-
thought. All normalized behind the wrapper; production Anthropic path byte-for-
byte unchanged (235 tests green).

### Phase 2 — Accuracy eval
**2a (live runs + screenshots):** the full Comparison agent runs **live on
Nemotron** end-to-end through the provider layer — first real proof, not a mock.
Side-by-side on the `campus-wifi` fixture (`scripts/eval_compare.py`): Claude is
verbose and adds domain knowledge with heavy hedging; **Nemotron is concise and
stays grounded in the supplied research** (even propagates source URLs into
cells), with honest `estimated` tagging throughout. Both produced complete,
valid 3×4 matrices. Qualitatively, Nemotron held up well for this structured-
synthesis task. Two small config findings (#4 wrong-`.env`, #5 script path).
Results saved under `results/`. NeMo Evaluator scoring is 2b.

**2b (LLM-as-judge scorecard):** the qualitative read got **numbers**. Ran the
spec's thin-script fallback for NeMo Evaluator (#7) — identical three-criterion
rubric, judged by `qwen/qwen3.5-122b-a10b` (a third family, distinct from both
models under test, self-preference guarded). The headline (#8) inverted the
"verbose = better" prior: **Nemotron out-scored the Claude baseline on cell
accuracy (4/5 vs 3/5)** by staying grounded, while Claude lost a point for
elaborating beyond the research. Both were perfect on completeness (5/5) and
confidence honesty (5/5) — neither over-claimed `confirmed`. The decision now
rests on a documented score, not a vibe: for grounded vendor synthesis,
**Nemotron is viable** — and on this fixture, marginally *more* faithful than the
incumbent. Scores: `results/campus-wifi__*__judge.json`.

### Phase 3 — Red-team
_pending_

### Phase 4 — Writeup
_pending_
