"""TCO Agent (PIS-11) — Total Cost of Ownership calculation.

The TCO calculation is **deterministic Python**, not an LLM call. PIS-09
requires Eval 1 and Eval 6 to be exact pytest unit tests, and a financial model
must never produce wrong arithmetic — so the math, the reasonableness check
(PIS-21), and the assumptions are computed here, reproducibly. The "agent"
boundary exists so downstream consumers depend on the stable `TCOResult`
contract (PIS-15).
"""

from __future__ import annotations

from app.schemas.tco import TCOFormInputs, TCOResult, YearCost

# PIS-21 — reasonableness thresholds. A per-unit figure between $0 and the
# threshold is suspiciously low (likely a total entered as a per-unit price).
# Exactly $0 is treated as a deliberate "no cost", not an anomaly.
_MIN_HARDWARE_PER_UNIT = 50.0
_MIN_LICENSING_PER_UNIT_YEAR = 20.0
# PID amendment 1.3 — additional thresholds for the new cost categories.
_MIN_ACCESSORIES_PER_UNIT = 5.0
_MAX_REASONABLE_SPARES_PERCENT = 50.0


def _reasonableness_warnings(inputs: TCOFormInputs) -> list[str]:
    """Flag anomalous per-unit costs before the model is trusted (PIS-21)."""
    warnings: list[str] = []
    if 0 < inputs.hardware_cost_per_unit < _MIN_HARDWARE_PER_UNIT:
        warnings.append(
            f"Hardware cost of ${inputs.hardware_cost_per_unit:,.2f} per unit is "
            f"unusually low (below ${_MIN_HARDWARE_PER_UNIT:,.0f}). Verify you "
            f"entered a per-unit price, not a total."
        )
    if 0 < inputs.licensing_cost_per_unit_year < _MIN_LICENSING_PER_UNIT_YEAR:
        warnings.append(
            f"Licensing cost of ${inputs.licensing_cost_per_unit_year:,.2f} per "
            f"unit per year is unusually low (below "
            f"${_MIN_LICENSING_PER_UNIT_YEAR:,.0f}). Verify the figure."
        )
    if 0 < inputs.accessories_cost_per_unit < _MIN_ACCESSORIES_PER_UNIT:
        warnings.append(
            f"Accessories cost of ${inputs.accessories_cost_per_unit:,.2f} per "
            f"unit is unusually low (below ${_MIN_ACCESSORIES_PER_UNIT:,.0f}). "
            f"Verify you entered a per-unit price, not a total."
        )
    if inputs.spares_percent > _MAX_REASONABLE_SPARES_PERCENT:
        warnings.append(
            f"Spares percentage of {inputs.spares_percent:.1f}% is unusually "
            f"high (above {_MAX_REASONABLE_SPARES_PERCENT:.0f}%). Verify this "
            f"is the intended ratio."
        )
    return warnings


def _assumptions(inputs: TCOFormInputs) -> list[str]:
    """Return the factual assumptions the model rests on.

    The first four lines are the original baseline (Eval 1 / PID v1.2). The
    remaining lines are conditional — they only appear when the corresponding
    cost category is non-zero, so unused categories stay out of the report.
    """
    lines = [
        f"Hardware is a one-time Year-1 capital cost "
        f"({inputs.device_count} units x ${inputs.hardware_cost_per_unit:,.2f}).",
        f"Licensing recurs every year at "
        f"${inputs.licensing_cost_per_unit_year:,.2f} per unit.",
        f"Support (Year 1) is ${inputs.support_cost_year_one:,.2f}; recurring "
        f"support from Year 2 onward is "
        f"${inputs.support_cost_recurring_per_year:,.2f} per year.",
        f"The model spans {inputs.lifecycle_years} year(s) and excludes "
        f"inflation and taxes.",
    ]
    if inputs.installation_cost > 0:
        lines.append(
            f"Installation / professional services is a one-time Year-1 cost of "
            f"${inputs.installation_cost:,.2f}."
        )
    if inputs.accessories_cost_per_unit > 0:
        lines.append(
            f"Accessories (mounts, cables, optics, PoE) are a one-time Year-1 "
            f"cost at ${inputs.accessories_cost_per_unit:,.2f} per unit "
            f"({inputs.device_count} units)."
        )
    if inputs.spares_percent > 0:
        lines.append(
            f"Spares are modeled as {inputs.spares_percent:.1f}% extra hardware "
            f"in Year 1, with no recurring licensing."
        )
    if inputs.training_cost > 0:
        lines.append(
            f"Migration / training labor is a one-time Year-1 cost of "
            f"${inputs.training_cost:,.2f}."
        )
    if inputs.adjacent_recurring_cost_per_year > 0:
        lines.append(
            f"Adjacent recurring cost (e.g. NAC renewal) is "
            f"${inputs.adjacent_recurring_cost_per_year:,.2f} per year, "
            f"applied to every year of the model."
        )
    return lines


def calculate_tco(scenario_name: str, inputs: TCOFormInputs) -> TCOResult:
    """Compute the year-by-year TCO model for a set of validated inputs.

    Cadence (PID amendment 1.3):
      * Year-1 only: hardware, support (bundled), installation, accessories,
        spares, training.
      * Recurring every year: licensing, adjacent_recurring.
      * Year 2+ only: support_recurring (renewal contract after Y1 bundle).

    Args:
        scenario_name: Human-readable name for this scenario.
        inputs: Validated TCO form inputs.

    Returns:
        TCOResult: year-by-year breakdown, 5-year total, assumptions, warnings.
    """
    year_by_year: list[YearCost] = []
    for year in range(1, inputs.lifecycle_years + 1):
        is_first_year = year == 1

        # Year-1 one-time costs
        hardware = (
            inputs.device_count * inputs.hardware_cost_per_unit
            if is_first_year
            else 0.0
        )
        support = inputs.support_cost_year_one if is_first_year else 0.0
        installation = inputs.installation_cost if is_first_year else 0.0
        accessories = (
            inputs.device_count * inputs.accessories_cost_per_unit
            if is_first_year
            else 0.0
        )
        spares = (
            inputs.device_count
            * (inputs.spares_percent / 100.0)
            * inputs.hardware_cost_per_unit
            if is_first_year
            else 0.0
        )
        training = inputs.training_cost if is_first_year else 0.0

        # Recurring costs
        licensing = inputs.device_count * inputs.licensing_cost_per_unit_year
        support_recurring = (
            0.0 if is_first_year else inputs.support_cost_recurring_per_year
        )
        adjacent_recurring = inputs.adjacent_recurring_cost_per_year

        total = (
            hardware
            + licensing
            + support
            + installation
            + accessories
            + spares
            + training
            + support_recurring
            + adjacent_recurring
        )
        year_by_year.append(
            YearCost(
                year=year,
                hardware=hardware,
                licensing=licensing,
                support=support,
                installation=installation,
                accessories=accessories,
                spares=spares,
                training=training,
                support_recurring=support_recurring,
                adjacent_recurring=adjacent_recurring,
                total=total,
            )
        )

    return TCOResult(
        scenario_name=scenario_name,
        inputs=inputs,
        year_by_year=year_by_year,
        total_5yr=sum(y.total for y in year_by_year),
        assumptions=_assumptions(inputs),
        warnings=_reasonableness_warnings(inputs),
    )
