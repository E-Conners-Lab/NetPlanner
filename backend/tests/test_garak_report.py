"""Unit tests for the Phase 3 garak report parser.

Turns garak's report JSONL (the ``eval`` records) into the runbook 03 pass-rate
table — per probe and rolled up per SPEC family. No network; synthetic JSONL.
"""

from __future__ import annotations

import json

from app.evals import garak_report as gr


def _eval(probe: str, detector: str, passed: int, fails: int, nones: int = 0) -> str:
    return json.dumps(
        {
            "entry_type": "eval",
            "probe": probe,
            "detector": detector,
            "passed": passed,
            "fails": fails,
            "nones": nones,
            "total_evaluated": passed + fails + nones,
            "total_processed": passed + fails + nones,
        }
    )


_REPORT = "\n".join(
    [
        json.dumps({"entry_type": "start_run setup"}),
        _eval("promptinject.HijackHateHumans", "promptinject.AttackRogueString", 19, 1),
        _eval("promptinject.HijackKillHumans", "promptinject.AttackRogueString", 18, 2),
        _eval(
            "latentinjection.LatentInjectionReport", "base.TriggerListDetector", 9, 1
        ),
        _eval("agent_breaker.AgentBreaker", "agent_breaker.ToolMisuse", 6, 0),
    ]
)


# --- parsing ------------------------------------------------------------------


def test_parse_records_skips_malformed_and_blank_lines() -> None:
    raw = _eval("promptinject.HijackHateHumans", "d", 5, 0) + "\n\nnot json\n"
    records = gr.parse_records(raw.splitlines())
    assert len(records) == 1
    assert records[0]["entry_type"] == "eval"


def test_eval_scores_extracts_passed_total_and_rate() -> None:
    scores = gr.eval_scores(gr.parse_records(_REPORT.splitlines()))
    by_probe = {s.probe: s for s in scores}
    hate = by_probe["promptinject.HijackHateHumans"]
    assert hate.passed == 19
    assert hate.total == 20
    assert hate.pass_rate == 0.95


def test_pass_rate_handles_zero_total() -> None:
    score = gr.EvalScore(probe="p", detector="d", passed=0, fails=0, nones=0, total=0)
    assert score.pass_rate == 0.0


def test_no_eval_entries_returns_empty() -> None:
    raw = "\n".join(
        json.dumps({"entry_type": t}) for t in ("start_run setup", "init", "attempt")
    )
    assert gr.eval_scores(gr.parse_records(raw.splitlines())) == []


# --- family rollup ------------------------------------------------------------


def test_family_of_extracts_prefix() -> None:
    assert gr.family_of("promptinject.HijackHateHumans") == "promptinject"
    assert gr.family_of("agent_breaker.AgentBreaker") == "agent_breaker"
    assert gr.family_of("noprefix") == "noprefix"


def test_rollup_by_family_sums_across_probes() -> None:
    scores = gr.eval_scores(gr.parse_records(_REPORT.splitlines()))
    families = {f.family: f for f in gr.rollup_by_family(scores)}
    # promptinject has two probes: (19+18) passed / (20+20) total.
    pi = families["promptinject"]
    assert pi.passed == 37
    assert pi.total == 40
    assert pi.pass_rate == 0.925
    assert pi.probe_count == 2


# --- attempt progress (partial / in-flight runs) ------------------------------


def test_attempt_progress_counts_completed_vs_total() -> None:
    raw = "\n".join(
        [
            json.dumps({"entry_type": "attempt", "status": 2}),
            json.dumps({"entry_type": "attempt", "status": 2}),
            json.dumps({"entry_type": "attempt", "status": 1}),
        ]
    )
    completed, total = gr.attempt_progress(gr.parse_records(raw.splitlines()))
    assert (completed, total) == (2, 3)


# --- rendering ----------------------------------------------------------------


def test_render_table_includes_probe_and_percentage() -> None:
    scores = gr.eval_scores(gr.parse_records(_REPORT.splitlines()))
    table = gr.render_table(scores)
    assert "promptinject.HijackHateHumans" in table
    assert "95.0%" in table
    assert "| Probe " in table  # markdown header


def test_render_family_table_rolls_up() -> None:
    scores = gr.eval_scores(gr.parse_records(_REPORT.splitlines()))
    table = gr.render_family_table(scores)
    assert "promptinject" in table
    assert "92.5%" in table
