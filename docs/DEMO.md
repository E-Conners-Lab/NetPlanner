# NetPlanner — Demo Walkthrough

A ~12-minute live walkthrough that produces a complete network refresh plan
from an empty dashboard. Written for a portfolio-style audience — works for
hiring managers, networking peers, or non-technical stakeholders by adding
or skipping the **🔎 deeper dive** tangents at each beat.

---

## What this demo proves

> *"NetPlanner takes a network engineer's refresh question and walks it all
> the way to a defensible plan — research, total cost of ownership, vendor
> comparison, and a stakeholder PDF — with governed AI in the middle and
> deterministic math wherever the answer must be reproducible."*

Three things to emphasize as you go, audience-appropriately:

1. **The agent layer is governed, not improvisational.** Multi-step AI work
   passes acceptance evals (7 of 7 on a versioned adversarial set) before
   it ships.
2. **The math is deterministic.** TCO and comparison aggregations are
   plain Python, not a model output — same inputs always give the same
   numbers. Pricing the model isn't sure about gets tagged `unavailable`,
   never fabricated.
3. **The output is something a CFO can read.** The end of the workflow is
   a branded PDF, not a chat transcript.

---

## Pre-flight (60 seconds before going live)

```bash
# Backend (tmux session np-be)
cd backend
env -u ANTHROPIC_API_KEY DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
  uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (tmux session np-fe)
cd frontend
npm run dev
```

Then in the browser, open `http://localhost:5173`. **Confirm before the demo:**

- The dashboard loads (HTTP 200, no console errors in dev tools).
- `/api/health` returns `{"status":"ok"}` from a quick curl.
- `ANTHROPIC_API_KEY` is in `backend/.env`, *not* exported in the parent shell
  (the `env -u` in the start command guards against this).
- If you've demoed before, delete prior projects so the dashboard starts empty.

> **Backup plan:** if streaming stalls mid-demo, refresh the page and re-ask
> the same question. The Advisor will replay deterministically; the model
> may have just been slow. Mention that the API isn't yours, you didn't
> build it, and a 3-second hiccup is not a bug to dwell on.

---

## The scenario you'll narrate

> *"Pacific Stamping is a mid-market manufacturer — three sites, around 600
> wired endpoints. Their access-layer stack is eight-year-old Catalyst 3850s
> at end of support. The CTO needs a refresh plan he can take to the CFO
> with a budget ceiling around $300,000, five-year horizon, and an honest
> comparison of two vendor lineups. He doesn't have time to build the model
> from scratch and the CFO won't accept 'ChatGPT said so.'"*

That sentence is the framing — write it on a sticky note and read it to the
audience verbatim before you start clicking. Everything that follows answers
the CTO's brief.

---

## The walkthrough

### Beat 1 — Set the scene (0:00 → 0:45)

**Show:** the empty Dashboard.

**Say:** *"This is the entry point. Every project is a network decision in
flight. Today we'll create one from scratch and walk it to a PDF the CTO
can hand his CFO."*

**🔎 deeper dive (hiring managers):** *"The architecture is FastAPI + async
SQLAlchemy on the backend, React + Vite on the frontend, Anthropic Claude for
the agent layer. The backend uses uv for dependency management and the
agent layer is tested with a versioned eval set — 7 acceptance scenarios
covering happy paths, edge cases, and silent-failure traps."*

---

### Beat 2 — Create the project (0:45 → 2:00)

**Click:** `New Project`.

**Fill in** (these values land cleanly):

| Field          | Value                                                                                |
|----------------|--------------------------------------------------------------------------------------|
| Name           | `Pacific Stamping — Access Layer Refresh`                                            |
| Company        | `Pacific Stamping Co.`                                                               |
| Description    | `Refresh aging Catalyst 3850 access layer across 3 sites, ~600 wired endpoints, end-of-support driving the timeline.` |
| Existing infra | `Cisco Catalyst 3850 stacks at HQ + 2 production sites, ~14 switches total, mixed 1G/10G uplinks, Meraki MR wireless.` |
| Budget ceiling | `300000`                                                                             |

**Click Save.** You land on the Project Overview.

**Say:** *"Notice the project carries the **constraints** — budget ceiling,
existing infra, scope — into every downstream agent. You're not re-typing
this anywhere."*

**🔎 deeper dive (peers):** *"On the backend, this maps to a `Project`
table and a `ProjectContext` Pydantic schema that gets injected into every
agent prompt. The agent doesn't re-read the database; the schema is the
contract."*

---

### Beat 3 — AI Advisor: scope and shape the problem (2:00 → 5:00)

**Click:** `AI Advisor` in the sidebar.

**Notice on the way in** — the new breadcrumb shows
`Dashboard › Pacific Stamping — Access Layer Refresh › AI Advisor`. Click
the project name in the breadcrumb to show it jumps back to overview.
Click back into Advisor.

**Type:**
> *Given a 600-endpoint access-layer refresh across 3 manufacturing sites
> with a $300K five-year ceiling, what device classes should I be
> considering, and what's the rough TCO shape I should plan around? I need
> to defend this to a CFO.*

**Watch the streaming response.** Point out as it lands:

- **CapEx/OpEx framing** appears explicitly — that came from a prompt-side
  fix during Phase 6 evals, not the model's default behavior.
- The Advisor **refuses to invent prices**. It will say "list prices vary;
  budget for X–Y per port" rather than hand you a fake number.
- It will recommend pulling specific vendors into the **Comparison** view
  next — that's the agent handing you off to the right tool.

**Say:** *"This is the only place in the workflow where I let the model
talk freely. Everything downstream is structured: tools, schemas,
deterministic math. The Advisor is the brainstorming partner; it's not
allowed to be the source of truth."*

**🔎 deeper dive (engineering):** *"The Advisor agent uses Sonnet 4.6 with
streaming and adaptive thinking. It has tools available — research and
project-context lookup — but it doesn't execute the math itself. That's
the separation that keeps the evals stable."*

---

### Beat 4 — TCO Calculator: Cisco scenario (5:00 → 7:30)

**Click:** `TCO Calculator` in the sidebar.

**Fill in the form** (these are illustrative; tune to your audience):

| Field                              | Value                              |
|------------------------------------|------------------------------------|
| Scenario Name                      | `Cisco Catalyst 9300 — 14 units`   |
| Device Count                       | `14`                               |
| Hardware Cost / Unit               | `12000`                            |
| Licensing Cost / Unit / Year       | `850`                              |
| Support Cost — Year 1              | `8500`                             |

**Click Preview.** The stacked bar chart renders.

**Point at the chart and walk it:**

- **Year 1** — the amber spike, the hardware capex hit (~$168K + first-year
  licensing + support).
- **Years 2–5** — flatter bars, just the OpEx tail (licensing recurring,
  support escalating slightly).
- **The total at the top right** is the 5-year sum the CFO actually cares
  about.

**Click Save.** The scenario appears in the saved list on the right.

**Say:** *"That's a real chart — recharts 3, verified to render correctly
end-to-end. And the math is deterministic Python — same inputs, same
numbers, every time. No LLM in the calculation path."*

**🔎 deeper dive (peers):** *"The chart and the table are fed by the same
`YearCost[]` payload from the backend. If the numbers ever disagree
between view and report, the bug is in serialization, not arithmetic."*

---

### Beat 5 — TCO Calculator: Arista scenario (7:30 → 8:30)

**In the saved-scenarios list**, hover the Cisco scenario → click
**Duplicate** (or re-enter values for a second scenario).

**Edit the form** for Arista:

| Field                              | Value                              |
|------------------------------------|------------------------------------|
| Scenario Name                      | `Arista CCS-720XP — 14 units`      |
| Hardware Cost / Unit               | `9500`                             |
| Licensing Cost / Unit / Year       | `600`                              |
| Support Cost — Year 1              | `6000`                             |

**Save.** You now have two scenarios side by side.

**Say:** *"Two scenarios, two charts, two 5-year totals. The user — the
CTO — can already see the gap. But this is just my numbers; I need an
explicit head-to-head."*

---

### Beat 6 — Vendor Comparison: the matrix (8:30 → 10:30)

**Click:** `Comparison` in the sidebar.

**Add two vendors:** `Cisco Catalyst 9300` and `Arista CCS-720XP`.

**Add five criteria:**
1. `Five-year TCO (qualitative)`
2. `Maximum port density`
3. `Operational maturity / ecosystem`
4. `Support model`
5. `Software upgrade story`

**Click Run.** The agent fills the matrix.

**Point at the confidence badges** in each cell — `high`, `medium`, `low`,
or `unavailable`. **Explicitly show an `unavailable` cell** if there is one.

**Say:** *"This is the discipline that separates governed AI from
improvisation. The agent has explicit permission to say 'I don't know'
about a specific cell — confidence is part of the contract, not a fig leaf.
If the CTO takes this to procurement, **every cell is sourced or flagged**.
There is no fabricated number."*

**🔎 deeper dive (engineering):** *"The `ComparisonCell` schema in
`backend/app/schemas/comparison.py` makes `confidence: unavailable` the
default — an unsourced cell is never presented as confirmed. That's a
post-eval-failure fix, not a v1 design choice."*

---

### Beat 7 — Reports: the stakeholder PDF (10:30 → 11:30)

**Click:** `Reports` in the sidebar → **Generate Report**.

A PDF is built server-side (WeasyPrint). Open it.

**Walk the audience through the PDF:**

- Cover page with the project name and a date.
- Executive summary — paragraph form, the kind the CFO actually reads.
- TCO chart embedded.
- Comparison matrix included.
- Recommendation with rationale.

**Say:** *"That's the artifact the CTO walks into the budget meeting with.
None of it was hand-typed. All of it is reproducible — the same project
generates the same report."*

---

### Beat 8 — Close (11:30 → 12:00)

**Land the plane:**

> *"That's the whole loop. Empty dashboard to defensible PDF in roughly
> twelve minutes. Three things to take away:*
>
> 1. *The AI helped at the bookends — scoping the problem and writing the
>    narrative — and stayed out of the math.*
> 2. *Every quantitative claim is either deterministic or confidence-tagged.*
> 3. *This is production-grade — the agent layer has versioned evals,
>    the backend has 95.58% test coverage, and the whole thing runs in
>    Docker. It's not a notebook demo."*

---

## Common audience questions, and how to answer

| Question                                                        | Answer                                                                                                                                       |
|-----------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| *"Why not just ask ChatGPT?"*                                   | "Because nothing about ChatGPT is reproducible, evaluated, or auditable. The same prompt gives a different number tomorrow. This is the governance layer above an LLM, not a wrapper around one." |
| *"What stops the model from hallucinating a price?"*            | "The Comparison schema defaults confidence to `unavailable`. Pricing the model is not sure about gets that tag rather than a fake dollar amount. Show the matrix — that's the cell-level proof." |
| *"How do you know it works?"*                                   | "Seven acceptance evals — happy paths, edge cases, silent-failure traps — pass on every prompt or model change. Block deploy on failure. The eval set is versioned in the repo." |
| *"Can it actually configure switches?"*                         | "No, and intentionally. NetPlanner is the **business-decision layer**, not configuration automation. Configuration belongs in NetBox + Nornir + your CI. This produces the plan; you implement it elsewhere." |
| *"Why Anthropic / Claude?"*                                     | "Tool use, streaming, structured output, and adaptive thinking are first-class. The Sonnet 4.6 + Haiku 4.5 split matches the agent tiers I needed — Sonnet for the Advisor, Haiku 4.5 for cheap research, Opus reserved for genuinely deep reasoning." |

---

## Tuning per audience

- **Hiring managers / engineering leaders** — keep all **🔎 deeper dive**
  blocks in. Add a 60-second appendix on the architecture and the agent
  tiering after Beat 8.
- **Networking peers** — replace the deeper-dive blocks with "this is what
  it would replace in your current workflow" — *the Excel TCO model, the
  Word vendor comparison, the slide deck for the CFO*.
- **Non-technical stakeholders** — skip the deeper-dive blocks entirely.
  Replace Beat 3's prompt with one closer to the audience's language
  (procurement, budget, risk).
- **Short-on-time variant (~6 min)** — skip Beat 5 (second TCO scenario),
  start Comparison with two vendors directly, and shorten the Advisor
  ask in Beat 3 to one question.

---

## If something goes wrong on stage

| Failure mode                                                | What to do                                                                                                                  |
|-------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| Advisor streaming stalls                                    | Refresh, re-ask. Mention API latency. Move on.                                                                              |
| PDF fails to generate (WeasyPrint native libs)              | Pre-generate one before the demo; have it ready to open in a second tab.                                                    |
| Comparison cell renders empty                               | Show it as proof of the `unavailable` default — *"that's the system telling you it doesn't know, exactly as it should."*    |
| Dev server has a stale state                                | Run `tmux kill-session -t np-be && tmux kill-session -t np-fe` and restart from Pre-flight.                                 |
| Anthropic key has been revoked / 401                        | Have the PDF and a screenshot deck ready as a fallback. The pre-built artifacts still tell the story.                       |

---

## After the demo

Two things to do every time:

1. **Delete the demo project** so the dashboard is clean for the next run.
2. **Write down any audience question you didn't have a clean answer for.**
   That's the next sharpening pass on this script.
