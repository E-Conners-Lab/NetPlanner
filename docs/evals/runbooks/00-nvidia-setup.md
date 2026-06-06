# Runbook 00 — NVIDIA API Catalog Setup

**Phase:** 0 · **Goal:** a scoped NVIDIA key and a Nemotron-first model shortlist.
**Status:** ✅ complete (2026-06-05)

---

## Objective

Get authenticated against the NVIDIA API catalog (NIM) and confirm the exact model
IDs for the shortlist, using the OpenAI-compatible endpoint.

## Prerequisites

- An email (personal or work) — no credit card, no identity verification.
- `curl` and Python 3.12 available.

## Steps

1. **Sign up** at <https://build.nvidia.com> and generate a personal key. It has
   the `nvapi-` prefix and unlocks every model in the catalog. Free tier is
   ~40 req/min, dev/eval only.
2. **Store it scoped** — add to `.env` (git-ignored), never inline:
   ```bash
   # .env  (NOT committed)
   NVIDIA_API_KEY=nvapi-...
   ```
3. **Pick the shortlist** from <https://build.nvidia.com/models> — Nemotron as the
   hero model, plus 1–2 comparators (e.g. a DeepSeek or Kimi reasoning model) for
   contrast. **Record the exact model IDs here** (they change; do not hardcode
   from memory):

   | Role | Catalog model ID | Notes |
   |---|---|---|
   | Hero (NVIDIA) | `nvidia/nemotron-3-super-120b-a12b` | Nemotron 3, reasoning; MoE ~12B active → fast on free tier |
   | Comparator A | `deepseek-ai/deepseek-v4-flash` | Frontier non-NVIDIA; answers directly (no CoT) |
   | Baseline | `claude-sonnet-4-6` | existing NetPlanner default |
   | Stretch (optional) | `nvidia/nemotron-3-ultra-550b-a55b` | Flagship; slower/heavier — comparison only if time allows |

   Confirmed present in the live catalog on 2026-06-05 via `GET /v1/models`.
   `deepseek-ai/deepseek-v4-pro` was the first comparator pick but **timed out
   (>30s, HTTP 000) repeatedly on the free tier** — swapped to the `-flash`
   variant, which returned cleanly. See issues log.

4. **Smoke-test the OpenAI-compatible endpoint** (base URL
   `https://integrate.api.nvidia.com/v1`):
   ```bash
   curl https://integrate.api.nvidia.com/v1/chat/completions \
     -H "Authorization: Bearer $NVIDIA_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"<MODEL_ID>","messages":[{"role":"user","content":"Reply with the single word: ready"}],"max_tokens":16}'
   ```

## Expected output

A JSON completion containing `ready`. A 401 means the key/header is wrong; a 429
means you hit the rate limit (wait, then retry). HTTP 000 from `curl` means the
request exceeded `--max-time` (model cold-start / slow on free tier).

## Results (2026-06-05)

- Key loaded from `.env` (70 chars, `nvapi-` prefix); `GET /v1/models` returned
  the full catalog.
- `nvidia/nemotron-3-super-120b-a12b` → **HTTP 200**. Note: emitted reasoning
  chain-of-thought (`"The user says…"`) before the answer — a 16-token cap
  truncated it mid-thought. **Lesson:** reasoning Nemotron needs generous
  `max_tokens` and a strip-the-thinking step downstream.
- `deepseek-ai/deepseek-v4-flash` → **HTTP 200 → `ready`** (direct answer, no CoT).
- `qwen/qwen3.5-122b-a10b` → **HTTP 200 → `ready`** (backup comparator).
- `deepseek-ai/deepseek-v4-pro` → **HTTP 000 (timeout >30s)** — rejected.

## Verification

- [x] Key in `.env`, not in any tracked file (`.env` git-ignored; `git grep`
      finds no `nvapi-`).
- [x] Smoke test returns 200 with content for hero + comparator.
- [x] Shortlist table filled with **real** model IDs from the live catalog.

## Issues encountered

Logged to `../ISSUES-LOG.md` (#1 reasoning-CoT truncation, #2 v4-pro timeout).

## Rollback

Delete the key from the NVIDIA dashboard; remove the `.env` line. No app changes
made in this phase.
