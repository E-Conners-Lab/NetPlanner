#!/usr/bin/env python
"""Phase 3 — summarize garak report JSONL into the runbook 03 pass-rate table.

Reads the reports produced by ``redteam/run_garak.sh`` and prints a per-probe
table plus a per-SPEC-family roll-up for each. For an in-flight run (no ``eval``
records yet) it reports attempt progress instead, so you can check on a long
sweep without waiting for it to finish.

Run from the backend/ directory:

    uv run python scripts/summarize_garak.py                 # all reports
    uv run python scripts/summarize_garak.py --report netplanner-advisor-injection

No network — pure parsing of local report files.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the `app` package importable when run as a plain script (mirrors the
# other eval scripts; pytest sets this via pythonpath, `python scripts/...` does
# not).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_REPO = Path(__file__).resolve().parents[2]
_RUNS = _REPO / "docs" / "evals" / "redteam" / "reports" / "garak_runs"


def _report_paths(name: str | None) -> list[Path]:
    if name:
        path = _RUNS / f"{name}.report.jsonl"
        return [path] if path.exists() else []
    return sorted(_RUNS.glob("*.report.jsonl"))


def _summarize_one(path: Path) -> None:
    from app.evals import garak_report as gr

    records = gr.parse_records(path.read_text().splitlines())
    scores = gr.eval_scores(records)

    print()
    print("=" * 78)
    print(f"  {path.name}")
    print("=" * 78)

    if not scores:
        completed, total = gr.attempt_progress(records)
        print(
            f"  No completed evals yet — {completed}/{total} attempts done "
            "(run still in flight, or detectors not run). Check back later."
        )
        return

    print("\n  Per probe:\n")
    print(gr.render_table(scores))
    print("\n  Per SPEC family:\n")
    print(gr.render_family_table(scores))


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize garak reports.")
    parser.add_argument(
        "--report",
        default=None,
        help="report prefix (no .report.jsonl); default: all reports",
    )
    args = parser.parse_args()

    paths = _report_paths(args.report)
    if not paths:
        raise SystemExit(
            f"No reports found in {_RUNS.relative_to(_REPO)}. "
            "Run docs/evals/redteam/run_garak.sh first."
        )
    for path in paths:
        _summarize_one(path)


if __name__ == "__main__":
    main()
