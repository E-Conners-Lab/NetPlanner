"""Automated eval tests for TCO calculation logic (PID Domain 2, PIS-09).

Eval 1 — happy-path TCO math.
Eval 6 — silent-failure guard: anomalous per-unit cost must be flagged.
"""

from __future__ import annotations

from app.agents.tco import calculate_tco
from app.schemas.tco import TCOFormInputs


def test_eval1_tco_happy_path() -> None:
    """PID Eval 1 — happy path.

    200 APs, $600 hardware/unit, $98/AP/year licensing, $0 support, 5-year
    lifecycle. Expected: Year 1 = $139,600; Years 2-5 = $19,600/year;
    5-year total = $218,000 (PID amendment 1.2). Match within 1%.
    """
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
        support_cost_year_one=0,
        lifecycle_years=5,
    )

    result = calculate_tco("Campus AP Refresh", inputs)

    assert len(result.year_by_year) == 5
    year1 = result.year_by_year[0]
    assert year1.year == 1
    assert year1.hardware == 120_000
    assert year1.licensing == 19_600
    assert year1.total == 139_600

    for follow_on in result.year_by_year[1:]:
        assert follow_on.hardware == 0
        assert follow_on.total == 19_600

    assert result.total_5yr == 218_000
    # Pass condition: within 1% of the manual figure.
    assert abs(result.total_5yr - 218_000) / 218_000 < 0.01


def test_eval6_anomalous_hardware_cost_is_flagged() -> None:
    """PID Eval 6 — silent-failure guard.

    Per-AP hardware entered as $6 instead of $600. The reasonableness check
    must flag it (PIS-21) so the user is warned before trusting the model.
    """
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=6,
        licensing_cost_per_unit_year=98,
    )

    result = calculate_tco("Anomalous scenario", inputs)

    assert result.warnings, "expected a reasonableness warning"
    assert any("per unit" in w for w in result.warnings)
    # The model is still computed — the warning gates trust, not computation.
    assert result.total_5yr > 0


def test_normal_costs_produce_no_warnings() -> None:
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
    )
    assert calculate_tco("Normal", inputs).warnings == []


def test_low_licensing_cost_is_flagged() -> None:
    # PIS-21: per-unit annual cost below $20 is also anomalous.
    inputs = TCOFormInputs(
        device_count=50,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=5,
    )
    warnings = calculate_tco("Low licensing", inputs).warnings
    assert any("Licensing" in w for w in warnings)


def test_zero_hardware_cost_does_not_warn() -> None:
    # $0 is a deliberate "reusing existing hardware", not a typo of $600.
    inputs = TCOFormInputs(
        device_count=100,
        hardware_cost_per_unit=0,
        licensing_cost_per_unit_year=120,
    )
    assert calculate_tco("Reused hardware", inputs).warnings == []


def test_support_applies_to_year_one_only() -> None:
    inputs = TCOFormInputs(
        device_count=10,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=100,
        support_cost_year_one=5_000,
    )
    result = calculate_tco("With support", inputs)
    assert result.year_by_year[0].support == 5_000
    assert all(y.support == 0 for y in result.year_by_year[1:])


def test_lifecycle_years_controls_breakdown_length() -> None:
    inputs = TCOFormInputs(
        device_count=10,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=100,
        lifecycle_years=3,
    )
    result = calculate_tco("Three year", inputs)
    assert len(result.year_by_year) == 3
    assert [y.year for y in result.year_by_year] == [1, 2, 3]


def test_result_carries_assumptions() -> None:
    inputs = TCOFormInputs(
        device_count=10,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=100,
    )
    assumptions = calculate_tco("Assumptions", inputs).assumptions
    assert assumptions
    assert any("one-time" in a for a in assumptions)
