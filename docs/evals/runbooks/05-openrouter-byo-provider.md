# Runbook 05 — OpenRouter BYO-Provider Spike (optional)

**Phase:** 5 (optional, post-engagement) · **Goal:** evaluate OpenRouter as the
production "bring-your-own-provider" path for NetPlanner v1.1.
**Status:** ⬜ not started — captured for later, not part of the core engagement.

---

## Why this is separate from the NVIDIA engagement

The core engagement (Phases 0–4) uses **LiteLLM → NVIDIA-direct** on purpose: it
showcases the NVIDIA ecosystem, spends NVIDIA's free tier with our own `nvapi-`
key, and keeps no third party in the request path. OpenRouter answers a
*different* question — *"what's the cleanest way to let end users pick from many
models with one integration?"* — which is a production UX concern, not an
NVIDIA-ecosystem showcase.

| | LiteLLM (Phases 0–4) | OpenRouter (this spike) |
|---|---|---|
| Layer | Open-source library, in-process | Hosted SaaS gateway |
| Keys / billing | Our key per provider (NVIDIA free tier direct) | One OpenRouter key + bill |
| Request path | Direct to provider | OpenRouter sits in the middle |
| Best for | Showcase, control, free-tier-direct | One-key-many-models for users |

They **compose**: LiteLLM has an `openrouter/` provider, and OpenRouter exposes an
OpenAI-compatible endpoint — so this slots behind the same `complete()` wrapper
with no rearchitecting.

## Hypothesis to test

OpenRouter gives NetPlanner users frontier + open model choice (incl. NVIDIA
models) through a single key and a single bill, with automatic fallback, at the
cost of (a) a third party in the data path and (b) per-token markup vs direct.

## Steps (when picked up)

1. Add `openrouter` to the `Provider` literal in `config.py` and an
   `openrouter_api_key` setting (+ fail-fast accessor).
2. Add an `_complete_openrouter()` branch to `app/agents/llm.py` — either via
   LiteLLM's `openrouter/<model>` prefix, or OpenRouter's OpenAI-compatible
   endpoint (`https://openrouter.ai/api/v1`). Reuse the thinking-strip helper.
3. Smoke-test one frontier and one open model through OpenRouter.
4. Compare against the engagement's NVIDIA-direct results on the **same**
   Comparison fixtures (latency, cost/token, output parity).

## Decision criteria

- **Data path / trust:** acceptable to route NetPlanner prompts through a third
  party for production? (Revisit SEC-13 / AI-3 — synthetic eval data is fine; real
  customer infrastructure data is the line.)
- **Cost:** OpenRouter markup vs direct-provider pricing at expected volume.
- **UX win:** does one-key-many-models materially simplify the BYO-provider
  feature vs wiring providers directly?

## Possible LinkedIn angle (distinct from the NVIDIA post)

*"One key, many models: evaluating OpenRouter for a production bring-your-own-
provider feature — and where a hosted gateway helps vs where direct-to-provider
wins."* Pairs with, but does not overlap, the NVIDIA-ecosystem post.

## Out of scope for now

This is a **stub**. It is not started, not committed to, and not required for the
core engagement's verdict. It exists so the idea is captured with its trade-offs
while fresh.
