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


# ---------------------------------------------------------------------------
# PID amendment 1.3 — additional cost categories
# ---------------------------------------------------------------------------


def test_amendment_1_3_defaults_preserve_eval1_total() -> None:
    """Eval 1 numbers must be unchanged when new fields default to zero."""
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
    )
    result = calculate_tco("Eval 1 with defaults", inputs)

    assert result.total_5yr == 218_000
    # Every new category should be exactly $0 on every year.
    for year in result.year_by_year:
        assert year.installation == 0
        assert year.accessories == 0
        assert year.spares == 0
        assert year.training == 0
        assert year.support_recurring == 0
        assert year.adjacent_recurring == 0


def test_installation_cost_is_year_one_only() -> None:
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
        installation_cost=25_000,
    )
    result = calculate_tco("With install", inputs)

    assert result.year_by_year[0].installation == 25_000
    assert all(y.installation == 0 for y in result.year_by_year[1:])
    # Year 1 total should be the original $139,600 + $25,000 install.
    assert result.year_by_year[0].total == 139_600 + 25_000
    assert result.total_5yr == 218_000 + 25_000


def test_accessories_cost_scales_with_device_count() -> None:
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
        accessories_cost_per_unit=40,
    )
    result = calculate_tco("With accessories", inputs)

    expected_accessories = 200 * 40
    assert result.year_by_year[0].accessories == expected_accessories
    assert all(y.accessories == 0 for y in result.year_by_year[1:])
    assert result.total_5yr == 218_000 + expected_accessories


def test_spares_percent_multiplies_hardware() -> None:
    # 10% spares of 200 APs at $600 = 20 spare units * $600 = $12,000.
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
        spares_percent=10,
    )
    result = calculate_tco("With spares", inputs)

    assert result.year_by_year[0].spares == 12_000
    assert all(y.spares == 0 for y in result.year_by_year[1:])
    assert result.total_5yr == 218_000 + 12_000


def test_training_cost_is_year_one_only() -> None:
    inputs = TCOFormInputs(
        device_count=10,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=100,
        training_cost=4_500,
    )
    result = calculate_tco("With training", inputs)

    assert result.year_by_year[0].training == 4_500
    assert all(y.training == 0 for y in result.year_by_year[1:])


def test_support_recurring_kicks_in_from_year_two() -> None:
    inputs = TCOFormInputs(
        device_count=10,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=100,
        support_cost_year_one=5_000,
        support_cost_recurring_per_year=2_000,
    )
    result = calculate_tco("With renewing support", inputs)

    assert result.year_by_year[0].support == 5_000
    assert result.year_by_year[0].support_recurring == 0
    for year in result.year_by_year[1:]:
        assert year.support == 0
        assert year.support_recurring == 2_000


def test_adjacent_recurring_applies_to_every_year() -> None:
    # e.g. an existing NAC contract renewing alongside the new fleet.
    inputs = TCOFormInputs(
        device_count=10,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=100,
        adjacent_recurring_cost_per_year=8_000,
    )
    result = calculate_tco("With NAC renewal", inputs)

    assert len(result.year_by_year) == 5
    for year in result.year_by_year:
        assert year.adjacent_recurring == 8_000
    # 5 years * $8k = $40k of additional recurring spend.
    baseline = 10 * 600 + 5 * (10 * 100)  # hardware + 5y licensing
    assert result.total_5yr == baseline + 5 * 8_000


def test_all_categories_combined_total_matches_sum_of_parts() -> None:
    """The 5-year total must equal the sum of every category across years."""
    inputs = TCOFormInputs(
        device_count=100,
        hardware_cost_per_unit=800,
        licensing_cost_per_unit_year=120,
        support_cost_year_one=4_000,
        installation_cost=15_000,
        accessories_cost_per_unit=30,
        spares_percent=5,
        training_cost=3_000,
        support_cost_recurring_per_year=1_500,
        adjacent_recurring_cost_per_year=2_000,
    )
    result = calculate_tco("Full stack", inputs)

    hardware = 100 * 800
    licensing_total = 5 * (100 * 120)
    support_y1 = 4_000
    installation = 15_000
    accessories = 100 * 30
    spares = 100 * 0.05 * 800
    training = 3_000
    support_recurring_total = 4 * 1_500  # Y2-Y5
    adjacent_total = 5 * 2_000

    expected = (
        hardware
        + licensing_total
        + support_y1
        + installation
        + accessories
        + spares
        + training
        + support_recurring_total
        + adjacent_total
    )
    assert result.total_5yr == expected


def test_low_accessories_cost_is_flagged() -> None:
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
        accessories_cost_per_unit=2,
    )
    warnings = calculate_tco("Low accessories", inputs).warnings
    assert any("Accessories" in w for w in warnings)


def test_high_spares_percent_is_flagged() -> None:
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
        spares_percent=75,
    )
    warnings = calculate_tco("Excessive spares", inputs).warnings
    assert any("Spares" in w for w in warnings)


def test_zero_accessories_does_not_warn() -> None:
    # $0 is the explicit "no accessories" default, not an anomaly.
    inputs = TCOFormInputs(
        device_count=200,
        hardware_cost_per_unit=600,
        licensing_cost_per_unit_year=98,
        accessories_cost_per_unit=0,
    )
    assert calculate_tco("No accessories", inputs).warnings == []


def test_legacy_saved_scenario_dict_deserializes() -> None:
    """Scenarios saved before amendment 1.3 must still load — Pydantic should
    accept dicts that omit the new fields and fill them with $0 defaults."""
    legacy_inputs_payload = {
        "device_count": 200,
        "hardware_cost_per_unit": 600,
        "licensing_cost_per_unit_year": 98,
        "support_cost_year_one": 0,
        "lifecycle_years": 5,
        "device_category": "access_point",
    }
    inputs = TCOFormInputs.model_validate(legacy_inputs_payload)
    assert inputs.installation_cost == 0
    assert inputs.spares_percent == 0
    assert inputs.support_cost_recurring_per_year == 0
    # And the computed total matches Eval 1.
    assert calculate_tco("Legacy", inputs).total_5yr == 218_000
