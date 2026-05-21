# NetPlanner — Project Initiation Document

**Version:** 1.2  
**Date:** 2026-05-18  
**Author:** Elliot Conner / The Tech-E LLC  
**Status:** Approved — Ready to Build

---

## Domain 1 — Intent Specification

**PIS-01 — One-sentence purpose:**
NetPlanner is an AI-powered business decision support tool that helps network engineers build TCO models, compare vendors, and generate stakeholder-ready reports without requiring finance or business expertise.

**PIS-02 — Capabilities at launch:**
1. Project management: create, edit, and delete planning scenarios with company name, description, existing infrastructure notes, and optional budget ceiling
2. Conversational AI Advisor with web search for live vendor pricing, scoped to project context, with streaming responses
3. TCO Calculator: structured form input → year-by-year cost model → chart visualization → save scenario to project
4. Vendor Comparison: select 2–3 platforms, define evaluation criteria, AI-generated comparison matrix with live pricing research and confidence indicators
5. Report generation: export any combination of TCO scenario, vendor comparison, and advisor conversation summary as a formatted, downloadable PDF
6. Persistent project and artifact storage via SQLite
7. Confidence tagging on all pricing data: `confirmed` (vendor-direct or major reseller source), `estimated` (indirect source), or `unavailable` (web search returned nothing usable)
8. Reasonableness validation on TCO inputs — flags anomalous per-unit costs before generating model
9. Report footer disclaimer on every export: pricing is for planning purposes only, verify with vendors before formal budget submission

**PIS-03 — Explicit exclusions (out of scope):**
- No SSH connectivity or live network device access — that is NetSensei's lane
- No network topology visualization or diagramming
- No real-time telemetry, alerting, or monitoring
- No multi-user or team collaboration features
- No cloud sync or remote access in MVP (local Docker Compose only)
- No integration with ITSM, ticketing, or procurement systems
- No financial modeling beyond 5-year TCO
- No automatic budget approval or submission workflows
- No presentation/slide deck generation (PDF report only)
- No configuration commands or remediation guidance — business layer only

**PIS-04 — Escalation path:**
- NetPlanner is advisory only. Every output is a recommendation for human review, never an automated action.
- When pricing data cannot be confirmed via web search: system flags as `unavailable`, surfaces the flag in the UI, and recommends contacting the vendor directly. Does not proceed with assumed values.
- When TCO form inputs are incomplete or contradictory: system prompts the user to correct them before generating the model. Never fills in missing financial inputs with defaults silently.
- When advisor confidence is low (e.g., question is outside business/network scope): system states its limitation and redirects the user to appropriate resources.
- No human-in-the-loop approval gate required for any action — all outputs are read-only advisory artifacts.

**PIS-05 — Functional correctness (measurable):**
- TCO Calculator: given valid inputs, produces a year-by-year breakdown that matches manual calculation within 1% margin
- Vendor Comparison: given two or more platform names and defined criteria, produces a matrix with at least one sourced data point per criterion per vendor
- Advisor: given a project context and a business justification question, produces a response that (a) references at least one vendor-specific pricing data point, (b) frames the answer in business language (ROI, TCO, CapEx/OpEx), and (c) avoids configuration or operational guidance
- Report: given at least one completed artifact, produces a downloadable PDF that renders all tables, charts, and text without truncation or formatting errors

---

## Domain 2 — Evaluation Design

**PIS-06/07/08 — Eval cases (5 required, 2 edge cases):**

| # | Type | Input | Expected Output | Pass Condition |
|---|---|---|---|---|
| 1 | Happy path — TCO | 200 APs, $600 hardware/unit, $98/AP/year licensing, $0 support Year 1, 5-year lifecycle | Year 1: $139,600. Years 2–5: $19,600/year. Total: $218,000 | Numbers match within 1% |
| 2 | Happy path — Advisor | Project: 200-AP campus. Question: "How do I justify a MIST deployment to my CFO?" | Response contains: CapEx/OpEx framing, at least one specific pricing figure, ROI narrative | All three elements present |
| 3 | Happy path — Comparison | Vendors: Juniper MIST vs Cisco Meraki. Criteria: licensing model, per-AP annual cost, API capability, AI/ML features, cloud management | Comparison matrix with all 5 criteria, data for both vendors, confidence indicators | All criteria populated, no empty cells |
| 4 | **Edge case — incomplete input** | TCO form submitted with device count but no hardware cost | System prompts for missing data; does not generate model | Zero TCO output produced; error prompt shown |
| 5 | **Edge case — pricing unavailable** | Vendor comparison includes a niche/obscure platform with no web search pricing results | Field marked `unavailable`; recommendation to contact vendor shown | No unverified price presented as confirmed |
| 6 | Silent failure — anomalous TCO | Per-AP hardware cost entered as $6 instead of $600; 200 APs | Reasonableness flag triggered; user warned before model generates | Warning surfaces; user must confirm to proceed |
| 7 | Edge case — vague advisor input | Question: "what should I buy?" with no project context set | System requests project context before answering | No generic vendor recommendation without context |

**PIS-09 — Eval execution method:**
- Evals 1, 6: pytest unit tests against TCO calculation logic (automated)
- Evals 4, 7: pytest integration tests against FastAPI routes (automated)
- Evals 2, 3, 5: manual review during development (LLM output — judgment-based with explicit checklist)
- All evals re-run before any feature merge

**PIS-10 — Minimum pass threshold:**
- 6 of 7 evals must pass to ship a feature
- Zero-tolerance failures (block ship regardless): Eval 4 (must never assume missing financial inputs) and Eval 5 (must never present unverified pricing as confirmed)

---

## Domain 3 — Agent Decomposition

**PIS-11 — Task breakdown:**

| Agent | Input | Output |
|---|---|---|
| Project Context Agent | Project DB record | Structured context JSON: `{name, company, description, existing_infra, budget_ceiling}` |
| Research Agent | Query string (vendor, product, pricing tier) | `{results: [{vendor, product, price_point, unit, source_url, confidence}]}` |
| TCO Agent | `{form_inputs, research_data, project_context}` | `{year_by_year: [{year, hardware, licensing, support, total}], total_5yr, assumptions, warnings}` |
| Comparison Agent | `{vendors, criteria, research_data, project_context}` | `{matrix: {vendor: {criterion: {value, source, confidence}}}, summary}` |
| Advisor Agent | `{messages, project_context, research_results}` | Streaming text response |
| Report Agent | `{project, artifacts: [tco\|comparison\|advisor_summary]}` | HTML string → WeasyPrint PDF bytes |

**PIS-12 — Dependency graph:**
```
Project Context Agent
        │
        ├──────────────────────────────┐
        ▼                              ▼
Research Agent ──────────────► TCO Agent ──────────────► Report Agent
        │                              │
        ├──────────────────────────────┤
        ▼                              ▼
Research Agent ──────────────► Comparison Agent ────────► Report Agent
        │
        ▼
Advisor Agent (multi-turn; invokes Research Agent as tool on demand)
```

**PIS-13 — Planner vs. single-shot classification:**
- All agents: single-shot except Advisor (multi-turn)
- No orchestrator/planner — FastAPI routes handle sequencing based on user action
- Advisor invokes Research as an internal tool call, not via a planner
- Rationale: scope is well-defined per action; planner adds complexity with no benefit here

**PIS-14 — Context window sizing:**
- Project context: ~500 tokens
- Conversation history (Advisor): hard cap at 20 messages; at 15, summarize oldest 10 into one system-level summary entry (~300 tokens); retain all recent messages
- Research results: cap at 3 results per query, ~1,000 tokens
- TCO inputs: ~300 tokens
- All tasks well within Sonnet 200k context window; no splitting required

**PIS-15 — Handoff contracts:**
- Project Context → all agents: `{name: str, company: str, description: str, existing_infra: str, budget_ceiling: float | null}`
- Research → TCO/Comparison/Advisor: `{query: str, results: [{vendor: str, product: str, price_point: str, unit: str, source_url: str, confidence: "confirmed" | "estimated" | "unavailable"}]}`
- TCO → Report: `{scenario_name: str, inputs: {...}, year_by_year: [{year: int, hardware: float, licensing: float, support: float, total: float}], total_5yr: float, assumptions: [str], warnings: [str]}`
- Comparison → Report: `{vendors: [str], criteria: [str], matrix: {str: {str: {value: str, source: str, confidence: str}}}, summary: str}`
- All contracts validated with Pydantic models in backend

---

## Domain 4 — Failure Mode Pre-Mortem

**PIS-16 — Context degradation strategy:**
- Advisor conversation history capped at 20 messages stored in session
- At 15 messages, auto-summarize oldest 10 into a single compressed system-level message
- Project context always re-injected fresh from the database at session start — never carried from prior conversation

**PIS-17 — Specification drift mitigation:**
- Every Advisor system prompt includes a hard anchor block:
  > "You are NetPlanner's business advisor. Your role is exclusively business decision support for network infrastructure planning: TCO, vendor justification, budget narratives, and ROI framing. Do not provide configuration commands, remediation steps, network troubleshooting, or operational guidance. If asked for anything outside this scope, state your limitation clearly and refer the user to appropriate technical resources."
- This block is injected as the first system message on every turn, not just session start

**PIS-18 — Input data validation:**
- TCO form inputs validated in React frontend before submission (required field checks, numeric type enforcement, range checks)
- Research results validated via Pydantic on receipt: `confidence` field must be one of the three allowed values; missing fields default to `unavailable`, never to assumed values
- All pricing data presented to downstream agents includes `confidence` and `source_url` — agents are instructed to propagate these, never strip them

**PIS-19 — Tool audit:**
- One tool in the harness: `web_search`
- Used exclusively by Research Agent
- Description is unambiguous: "Search the web for current vendor pricing, product specifications, and licensing terms for network infrastructure equipment and software."
- No tool confusion risk — single tool, single agent

**PIS-20 — Cascading failure gates:**
- Research Agent failure → TCO and Comparison agents receive `{results: [], confidence: "unavailable"}`; proceed with warning flags visible in UI; do not fail silently
- TCO Agent failure → Report Agent receives error state; generates partial report with explicit error notice rather than empty/corrupt output
- Project Context Agent failure → all downstream agents blocked at the route level; user shown a clear error with retry option

**PIS-21 — Silent failure definition and eval:**
- Silent failure profile: TCO model with mathematically correct but contextually nonsensical numbers (e.g., per-unit cost entered as total cost → 5-year TCO of $120 for a 200-AP campus)
- Detection: TCO Agent includes reasonableness check — if calculated per-unit annual cost falls below $20 or hardware cost per device below $50 for any standard network device category, surface a warning before completing the model
- Eval 6 above covers this case explicitly

---

## Domain 5 — Trust and Guardrail Design

**PIS-22 — Action classification:**
| Action | Classification |
|---|---|
| Web search (Research Agent) | Read-only |
| Generate TCO model | Read-only (ephemeral compute) |
| Generate comparison matrix | Read-only (ephemeral compute) |
| Advisor conversation turn | Read-only |
| Save project / scenario / comparison | Reversible write |
| Export PDF report | Read-only (file generation) |
| Delete project | Reversible write (confirmation dialog required) |
| No irreversible writes exist in scope | — |

**PIS-23 — Blast radius assessment:**
- Worst case: user exports a report with incorrect TCO figures and presents it to leadership, resulting in a flawed budget submission
- Mitigation: every PDF report includes a mandatory footer: *"NetPlanner outputs are estimates for planning purposes only. All pricing should be verified directly with vendors before formal budget submission."*
- No network devices, financial systems, or production infrastructure are touched — blast radius is limited to a planning document the user chooses to act on

**PIS-24 — Hard stop guardrails (system prompt level):**
1. Never present unverified pricing as confirmed — confidence indicator must always be surfaced
2. Never provide network device configuration commands or CLI syntax
3. Never recommend a single vendor without presenting at least one alternative or framing tradeoffs
4. Always include the disclaimer on every report export — it is not optional
5. Never generate financial projections beyond 5 years (outside reasonable planning horizon)

---

## Domain 6 — Context Architecture

**PIS-25 — Context classification:**
| Data | Classification |
|---|---|
| Project metadata | Persistent (SQLite) |
| Saved TCO scenarios | Persistent (SQLite) |
| Saved vendor comparisons | Persistent (SQLite) |
| Advisor conversation history | Per-session (in-memory during session, written to SQLite on session end) |
| Research results | Per-session (not persisted; re-run if needed) |
| TCO calculations | Ephemeral (computed on demand; persisted only on explicit user save) |
| Comparison matrices | Ephemeral (computed on demand; persisted only on explicit user save) |

**PIS-26 — Retrieval strategy:**
- No RAG / vector store in MVP — web search handles live pricing retrieval
- Web search: top 3 results per query, no reranking in MVP
- Future consideration: ChromaDB pricing database for offline/faster lookups if web search latency becomes a UX issue

**PIS-27 — Dirty data risks:**
- Web search may return outdated pricing pages, reseller markups, or promotional prices
- Mitigation: Research Agent always extracts and returns source URL and publication date where available; confidence defaults to `estimated` unless source is identifiable as vendor-official or Tier-1 reseller (CDW, Insight, SHI); `confirmed` requires explicit vendor pricing page or official datasheet

---

## Domain 7 — Cost and Token Economics

**PIS-28 — Token budget (per run):**

| Component | Tokens |
|---|---|
| System prompt (Advisor) | ~800 |
| Project context | ~500 |
| Conversation history (avg) | ~3,000 |
| Research results | ~1,000 |
| Output (avg) | ~800 |
| **Total Advisor run** | **~6,100 → 9,150 with 1.5x buffer** |
| TCO/Comparison run (input + output) | ~4,500 |
| Research/Haiku run | ~1,500 |

**PIS-29 — Model assignments:**

| Role | Model | Rationale |
|---|---|---|
| Advisor Agent | claude-sonnet-4-6 | Multi-turn reasoning, business language generation, nuance |
| TCO Agent | claude-sonnet-4-6 | Structured math reasoning + narrative output |
| Comparison Agent | claude-sonnet-4-6 | Multi-vendor synthesis with sourced data |
| Report Agent | claude-sonnet-4-6 | Formatting and narrative generation |
| Research Agent | claude-haiku-4-5 | Web search + structured data extraction — fast and cost-efficient |

**PIS-30 — ROI calculation:**

| Metric | Value |
|---|---|
| Advisor runs/day (est.) | 10 |
| TCO/Comparison runs/day (est.) | 5 |
| Research runs/day (est.) | 15 |
| Estimated monthly cost | ~$6–10/month |
| Value delivered | Interview prep, content creation, The Tech-E platform foundation, future product optionality |
| ROI justified | ✅ Yes |

---

## Build Order

| Phase | Deliverable |
|---|---|
| 0 | Project scaffold: FastAPI backend, React frontend, SQLite, Docker Compose |
| 1 | Projects CRUD (backend routes + frontend UI) |
| 2 | Research Agent + Advisor with streaming (core AI layer) |
| 3 | TCO Calculator (form, agent, chart visualization) |
| 4 | Vendor Comparison (form, agent, matrix UI) |
| 5 | Report generation (PDF export via WeasyPrint) |
| 6 | Polish pass: design refinement, error states, eval run |

---

## Pre-Build Checklist

```
[x] One-sentence purpose written and fits on one line               (PIS-01)
[x] All launch capabilities listed with specifics                   (PIS-02)
[x] Explicit exclusions documented                                  (PIS-03)
[x] Escalation trigger and handoff defined                          (PIS-04)
[x] Functional correctness defined in measurable terms              (PIS-05)
[x] Five eval cases written, two edge cases included                (PIS-06/07/08)
[x] Eval execution method named                                     (PIS-09)
[x] Minimum pass threshold set                                      (PIS-10)
[x] Tasks decomposed to single-input / single-output units          (PIS-11)
[x] Dependency graph drawn                                          (PIS-12)
[x] Planner vs. single-shot decision made per task                  (PIS-13)
[x] Tasks sized to available context window                         (PIS-14)
[x] Handoff contracts defined between all agents                    (PIS-15)
[x] Context degradation strategy documented                         (PIS-16)
[x] Spec drift mitigation in system prompt design                   (PIS-17)
[x] Input data validated upstream of agent                          (PIS-18)
[x] All tools audited for description clarity                       (PIS-19)
[x] Cascading failure gates placed                                  (PIS-20)
[x] Silent failure eval written                                     (PIS-21)
[x] Actions classified read / reversible / irreversible             (PIS-22)
[x] Blast radius assessed and documented                            (PIS-23)
[x] Hard stop guardrails defined in system prompt design            (PIS-24)
[x] Context classified persistent / per-session / ephemeral        (PIS-25)
[x] Retrieval strategy documented                                   (PIS-26)
[x] Dirty data risks identified and mitigated                       (PIS-27)
[x] Token budget estimated                                          (PIS-28)
[x] Model assignments documented with rationale                     (PIS-29)
[x] ROI calculation completed and justified                         (PIS-30)
[x] PID filed at docs/PID.md before first meaningful commit
```

---

## Amendments

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-05-18 | Initial PID |
| 1.1 | 2026-05-18 | Domain 7 (PIS-29): Sonnet-tier model updated `claude-sonnet-4-5` → `claude-sonnet-4-6` (current successor; same cost basis). Approved at Phase 2 kickoff. |
| 1.2 | 2026-05-18 | Domain 2 (Eval 1): corrected the 5-year total from `$198,400` to `$218,000`. The original total summed only 4 years of licensing; the breakdown (Year 1 + four recurring years at $19,600) sums to $218,000. Approved at Phase 3 kickoff. |
| 1.3 | 2026-05-21 | Domains 2, 3, 4 (PIS-15, PIS-18, PIS-21, Eval 1): TCO contract extended with six optional cost categories to model real refresh spend surfaced during the Riverbend Health run. `TCOFormInputs` gains `installation_cost` (Y1 flat), `accessories_cost_per_unit` (Y1 × device_count), `spares_percent` (Y1 × device_count × hardware_cost_per_unit), `training_cost` (Y1 flat), `support_cost_recurring_per_year` (Y2+ recurring), `adjacent_recurring_cost_per_year` (Y1–Y5 recurring). `YearCost` (PIS-15) gains matching fields: `installation`, `accessories`, `spares`, `training`, `support_recurring`, `adjacent_recurring`. All new fields default to `0.0` — an explicit user choice ("no cost here"), not a silent default of a missing required input (Eval 4 preserved). Eval 1 figures unchanged ($218,000 5-year total) because all new fields default to zero. PIS-21 reasonableness checks extended: per-unit accessories below $5 flagged; spares above 50% flagged. Existing `support_cost_year_one` semantics unchanged (Y1-only bundled support); recurring support contracts begin Y2 via the new field. Backward compatibility: scenarios saved before this amendment load unchanged — Pydantic defaults absorb the missing fields. Approved at start of TCO refresh work. |