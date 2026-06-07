# LinkedIn draft — NVIDIA Nemotron eval (DRAFTED, NOT POSTED)

> Review before posting. Verdict and numbers must match [`RESULTS.md`](RESULTS.md).
> Publish checklist (runbook 04): no keys / paths / PII in text or images;
> claims match the committed tables; free-tier/not-production caveat stated;
> NVIDIA tools named; verdict tied to data.

---

## Post body (copy-paste ready)

I asked a simple question about my own product: could NVIDIA's Nemotron reasoning model stand in for Claude inside NetPlanner's AI agents, and could I prove it with NVIDIA's own tooling instead of vibes?

So I eval-gated and red-teamed my own production agents end to end on NVIDIA's stack: Nemotron as the model, LiteLLM to route to it, a NeMo Evaluator rubric to score accuracy, and garak to attack it. The whole thing was measured against the Secure Build Standard I already hold my own code to.

Two results stood out.

On accuracy, the eval gate disagreed with my prior. I expected the verbose incumbent to win. An independent LLM judge (Qwen on NVIDIA's catalog, chosen so neither model under test could grade itself) scored Nemotron 4/5 on cell accuracy versus Claude's 3/5, because Nemotron stayed grounded in the supplied research while Claude elaborated with plausible detail the data never contained. Both were perfect on completeness and on honest confidence tagging. For grounded, structured synthesis, restraint beat elaboration.

On safety, the red-team earned its keep. I made garak attack the real Advisor with its actual production system prompt loaded, not a bare model (an easy mistake that produces a falsely clean report). Indirect prompt injection, the exact attack class my agents face when they read untrusted research and project data, got past the system-prompt guardrails about 79% of the time. That is not an exploit of my app, because the app does not rely on the prompt alone: it uses a structural boundary fence and schema-constrained tool calls. But it is hard evidence for a rule I already follow: a prompt instruction is not a security control. Structure is.

The verdict: viable, with caveats. Nemotron is a credible backend for my structured-synthesis agent, but it is not a flag-flip drop-in. It is a reasoning model, so its output shape differs, and its tool-use behavior differs enough that one agent looped a research tool to its limit on questions Claude answered directly. Each of those needed real handling.

The honest part: this was a free dev tier, one fixture, one judge, and a partial red-team that throttling cut short. It decides whether deeper work is worth doing, not that the migration is done.

The best material came from the scars. A reasoning model is not a drop-in. Swapping models changes tool-use behavior, not just answer quality. And a red-team tool with no request timeout will happily hang for 80 minutes on one stalled connection until you pin one. Those are the lessons I would not have gotten from a benchmark table.

If you build agent apps: eval-gate and red-team your model swaps with the provider's own tools, put your real system prompt in front of the probes, and never trust a prompt to do a firewall's job.

#AIEngineering #LLM #NVIDIA #Nemotron #AIsecurity #PromptInjection #Evals

---

## Suggested attachments (strip secrets/paths first — SEC-12/18)

1. The Phase 2b accuracy table (Claude 3/5 vs Nemotron 4/5) — clean and punchy.
2. A garak terminal shot showing the latent-injection pass-rate. **Crop the prompt
   line / `/Users/elliotconner/` path** if you'd rather not show the local account.
3. Optional: the provider-flag diff (one wrapper, two providers) to make the
   "ecosystem fluency" point visual.

## Notes for review

- Tone is first-person, scar-forward, no hype; numbers match `RESULTS.md`.
- "~79%" and "4/5 vs 3/5" are the load-bearing claims — keep them exact.
- Keeps the not-production / free-tier caveat explicit (credibility).
- Does not claim a Claude-vs-Nemotron *safety* comparison (only Nemotron was
  garak-targeted) — the post is careful to say injection got past the guardrails,
  not "Nemotron is less safe than Claude."
