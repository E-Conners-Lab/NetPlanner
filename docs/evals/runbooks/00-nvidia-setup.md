# Runbook 00 — NVIDIA API Catalog Setup

**Phase:** 0 · **Goal:** a scoped NVIDIA key and a Nemotron-first model shortlist.
**Status:** ⬜ not started

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
   | Hero (NVIDIA) | `nvidia/…` _(fill from catalog)_ | Nemotron reasoning |
   | Comparator A | `…` | |
   | Baseline | `claude-sonnet-4-6` | existing NetPlanner default |

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
means you hit the rate limit (wait, then retry).

## Verification

- [ ] Key in `.env`, not in any tracked file (`git grep nvapi-` returns nothing).
- [ ] Smoke test returns a 200 with content.
- [ ] Shortlist table above filled with **real** model IDs.

## Issues encountered

_Append to `../ISSUES-LOG.md`; summarize the post-worthy ones here._

## Rollback

Delete the key from the NVIDIA dashboard; remove the `.env` line. No app changes
made in this phase.
