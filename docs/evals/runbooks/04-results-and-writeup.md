# Runbook 04 — Results & Writeup

**Phase:** 4 · **Goal:** turn the evidence into a verdict and a publishable post.
**Status:** ⬜ not started

---

## Objective

Synthesize phases 0–3 into (a) a one-paragraph engineering verdict and (b) a
LinkedIn draft that demonstrates NVIDIA-ecosystem and AI-development skill.

## Inputs

- NeMo Evaluator results table (Runbook 02).
- garak report + table (Runbook 03).
- The full issues log (`../ISSUES-LOG.md`) — the snags *are* the story.

## Steps

1. **Write the verdict** — *viable / viable-with-caveats / not-yet* — anchored to
   the numbers (accuracy scores + red-team hit-rates), not impressions.
2. **Assemble the results section** — the two tables, plus the 2–3 most
   instructive issues with their fixes.
3. **Draft the post** around the through-line:
   *I red-teamed and eval-gated my own production agents with NVIDIA's stack,
   against my own published Secure Build Standard.* Beats:
   - The question (can Nemotron stand in for Claude in a real agent app?)
   - The NVIDIA stack used (Nemotron · LiteLLM · NeMo Evaluator · garak)
   - One concrete issue + fix (the credibility hook — engineers trust scars)
   - The numbers (accuracy + safety)
   - The verdict and what's next
4. **Screenshots/artifacts** — eval table, a garak report snippet (redacted),
   the provider-flag diff. Strip any secrets/PII before publishing (SEC-12/18).

## Publish checklist

- [ ] No keys, tokens, internal paths, or PII in text or images (SEC-12/18).
- [ ] Claims match the committed results tables (no inflation).
- [ ] Free-tier / not-production caveat stated.
- [ ] NVIDIA tools credited by name (Nemotron, NIM, NeMo Evaluator, garak).
- [ ] Verdict is falsifiable and tied to data.

## Output

- `docs/evals/RESULTS.md` — the consolidated results + verdict (committed).
- LinkedIn draft — per the launch-status note, drafted-not-posted until reviewed.

> Tie-in: the prior public-launch post said more model choice was coming. This
> engagement is the receipt for that promise.
