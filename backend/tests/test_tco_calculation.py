"""Automated eval tests for TCO calculation logic (PID Domain 2, PIS-09).

Eval 1 — happy-path TCO math.
Eval 6 — silent-failure guard: anomalous per-unit cost must be flagged.

Phase-0 stubs: marked ``skip`` so they collect with zero failures. The
assertions are filled in alongside the TCO Agent in Phase 3.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Eval 1 — TCO math: logic implemented in Phase 3")
def test_eval1_tco_happy_path() -> None:
    """PID Eval 1 — happy path.

    Inputs: 200 APs, $600 hardware/unit, $98/AP/year licensing, $0 support
    in Year 1, 5-year lifecycle.

    Expected: Year 1 = $139,600; Years 2-5 = $19,600/year;
    5-year total = $198,400. Pass condition: numbers match within 1%.
    """
    raise AssertionError("not implemented")


@pytest.mark.skip(reason="Eval 6 — reasonableness check: logic implemented in Phase 3")
def test_eval6_anomalous_tco_flagged() -> None:
    """PID Eval 6 — silent-failure guard.

    Inputs: per-AP hardware cost entered as $6 instead of $600, 200 APs.

    Expected: the reasonableness flag triggers and the user is warned before
    the model generates. Pass condition: a warning surfaces and the user must
    confirm to proceed.
    """
    raise AssertionError("not implemented")
