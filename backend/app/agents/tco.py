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
    return warnings


def _assumptions(inputs: TCOFormInputs) -> list[str]:
    """Return the factual assumptions the model rests on."""
    return [
        f"Hardware is a one-time Year-1 capital cost "
        f"({inputs.device_count} units x ${inputs.hardware_cost_per_unit:,.2f}).",
        f"Licensing recurs every year at "
        f"${inputs.licensing_cost_per_unit_year:,.2f} per unit.",
        f"Support is modeled as a Year-1 cost only "
        f"(${inputs.support_cost_year_one:,.2f}); recurring support is excluded.",
        f"The model spans {inputs.lifecycle_years} year(s) and excludes "
        f"inflation and taxes.",
    ]


def calculate_tco(scenario_name: str, inputs: TCOFormInputs) -> TCOResult:
    """Compute the year-by-year TCO model for a set of validated inputs.

    Hardware is a one-time Year-1 cost; licensing recurs annually; support is a
    Year-1-only cost (per the `support_cost_year_one` input). Returns the
    TCO -> Report handoff contract (PIS-15), including reasonableness
    `warnings` (PIS-21).

    Args:
        scenario_name: Human-readable name for this scenario.
        inputs: Validated TCO form inputs.

    Returns:
        TCOResult: year-by-year breakdown, 5-year total, assumptions, warnings.
    """
    year_by_year: list[YearCost] = []
    for year in range(1, inputs.lifecycle_years + 1):
        is_first_year = year == 1
        hardware = (
            inputs.device_count * inputs.hardware_cost_per_unit
            if is_first_year
            else 0.0
        )
        licensing = inputs.device_count * inputs.licensing_cost_per_unit_year
        support = inputs.support_cost_year_one if is_first_year else 0.0
        year_by_year.append(
            YearCost(
                year=year,
                hardware=hardware,
                licensing=licensing,
                support=support,
                total=hardware + licensing + support,
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
