"""Phase 3 — parse garak report JSONL into the runbook 03 pass-rate table.

garak writes one JSON object per line; the authoritative scores live in its
``eval`` records (one per probe × detector), emitted after a probe's detectors
finish. Each carries ``passed`` / ``fails`` / ``nones`` and ``total_evaluated``;
the **pass-rate** = ``passed / total_evaluated`` — the fraction of generations
that *resisted* the attack (higher = safer).

This turns a finished (or in-flight) report into a per-probe table and a per-SPEC
family roll-up, ready to paste into runbook 03. No network — pure parsing.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class EvalScore:
    """One garak ``eval`` record: a probe × detector pass tally."""

    probe: str
    detector: str
    passed: int
    fails: int
    nones: int
    total: int

    @property
    def pass_rate(self) -> float:
        """Fraction of generations that resisted the attack (0.0 if none ran)."""
        return self.passed / self.total if self.total else 0.0


@dataclass(frozen=True)
class FamilyScore:
    """A SPEC probe family (e.g. ``promptinject``), rolled up across probes."""

    family: str
    passed: int
    fails: int
    total: int
    probe_count: int

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


def parse_records(lines: Iterable[str]) -> list[dict]:
    """Parse JSONL into dicts, skipping blank and malformed lines."""
    records: list[dict] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def eval_scores(records: Iterable[dict]) -> list[EvalScore]:
    """Extract the ``eval`` records as :class:`EvalScore`, in report order."""
    scores: list[EvalScore] = []
    for rec in records:
        if rec.get("entry_type") != "eval":
            continue
        passed = int(rec.get("passed", 0))
        fails = int(rec.get("fails", 0))
        nones = int(rec.get("nones", 0))
        total = int(rec.get("total_evaluated", passed + fails + nones))
        scores.append(
            EvalScore(
                probe=str(rec.get("probe", "")),
                detector=str(rec.get("detector", "")),
                passed=passed,
                fails=fails,
                nones=nones,
                total=total,
            )
        )
    return scores


def family_of(probe: str) -> str:
    """The garak probe family — the module prefix before the first dot."""
    return probe.split(".", 1)[0]


def rollup_by_family(scores: Iterable[EvalScore]) -> list[FamilyScore]:
    """Aggregate per-probe scores into per-family totals (report order)."""
    order: list[str] = []
    acc: dict[str, dict[str, int]] = {}
    for score in scores:
        fam = family_of(score.probe)
        if fam not in acc:
            acc[fam] = {"passed": 0, "fails": 0, "total": 0, "probes": 0}
            order.append(fam)
        acc[fam]["passed"] += score.passed
        acc[fam]["fails"] += score.fails
        acc[fam]["total"] += score.total
        acc[fam]["probes"] += 1
    return [
        FamilyScore(
            family=fam,
            passed=acc[fam]["passed"],
            fails=acc[fam]["fails"],
            total=acc[fam]["total"],
            probe_count=acc[fam]["probes"],
        )
        for fam in order
    ]


def attempt_progress(records: Iterable[dict]) -> tuple[int, int]:
    """Return (completed, total) attempt counts — for in-flight/partial runs.

    garak marks an attempt ``status == 2`` once its generations are done.
    """
    completed = total = 0
    for rec in records:
        if rec.get("entry_type") != "attempt":
            continue
        total += 1
        if rec.get("status") == 2:
            completed += 1
    return completed, total


def _pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def render_table(scores: Iterable[EvalScore]) -> str:
    """Markdown per-probe table: probe, detector, passed/total, pass-rate."""
    rows = [
        "| Probe | Detector | Passed/Total | Pass-rate |",
        "|---|---|---|---|",
    ]
    for s in scores:
        rows.append(
            f"| {s.probe} | {s.detector} | {s.passed}/{s.total} | {_pct(s.pass_rate)} |"
        )
    return "\n".join(rows)


def render_family_table(scores: Iterable[EvalScore]) -> str:
    """Markdown per-family roll-up: family, probes, passed/total, pass-rate."""
    rows = [
        "| Probe family | Probes | Passed/Total | Pass-rate |",
        "|---|---|---|---|",
    ]
    for f in rollup_by_family(scores):
        rows.append(
            f"| {f.family} | {f.probe_count} | {f.passed}/{f.total} | "
            f"{_pct(f.pass_rate)} |"
        )
    return "\n".join(rows)
