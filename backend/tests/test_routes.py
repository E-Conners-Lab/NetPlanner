"""Automated eval tests for FastAPI routes (PID Domain 2, PIS-09).

Eval 4 — edge case: incomplete TCO input must not generate a model.
Eval 7 — edge case: vague advisor input must request project context first.

Both are zero-tolerance / edge-case evals (PIS-10). Phase-0 stubs: marked
``skip`` so they collect with zero failures; assertions land in Phase 3/4.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Eval 4 — incomplete TCO input: logic implemented in Phase 3")
def test_eval4_incomplete_tco_input_is_rejected() -> None:
    """PID Eval 4 — incomplete input edge case.

    Input: TCO form submitted with a device count but no hardware cost.

    Expected: the system prompts for the missing data and does NOT generate a
    model. Pass condition: zero TCO output produced; an error prompt is shown.
    Zero-tolerance: financial inputs are never silently assumed (PIS-04/PIS-10).
    """
    raise AssertionError("not implemented")


@pytest.mark.skip(reason="Eval 7 — vague advisor input: logic implemented in Phase 2")
def test_eval7_vague_advisor_input_requires_context() -> None:
    """PID Eval 7 — vague advisor input edge case.

    Input: the question "what should I buy?" with no project context set.

    Expected: the system requests project context before answering. Pass
    condition: no generic vendor recommendation is produced without context.
    """
    raise AssertionError("not implemented")
