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
_pending_

### Phase 2 — Accuracy eval
_pending_

### Phase 3 — Red-team
_pending_

### Phase 4 — Writeup
_pending_
