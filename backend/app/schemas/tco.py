"""Pydantic schemas for the TCO Calculator, including the Report handoff."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RefreshEvent(BaseModel):
    """A mid-cycle hardware refresh inside a TCO lifecycle (PID amendment 1.5).

    Modelled as an additive hardware spend in a specific year. Refreshed units
    re-use the existing licensing line (same fleet size), so only hardware
    cost moves; licensing, support, and adjacent recurring are unaffected.

    `cost_per_unit_override` lets the user model "new gear is cheaper / more
    expensive than the original purchase" without editing the base input.
    Leaving it `None` means refreshed units cost the same per unit as the
    initial deployment.
    """

    model_config = ConfigDict(from_attributes=True)

    year: int = Field(
        ...,
        ge=2,
        le=5,
        description=(
            "Year the refresh occurs. Year 1 is the initial deployment so "
            "refresh events start at Year 2; cap follows PIS-24 #4 (5-year)."
        ),
    )
    percent_of_devices: float = Field(
        ...,
        gt=0,
        le=100,
        description="Percentage of the fleet refreshed in this year (0 < pct <= 100).",
    )
    cost_per_unit_override: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Optional override cost per refreshed unit. If None, the original "
            "hardware_cost_per_unit is used."
        ),
    )


class TCOFormInputs(BaseModel):
    """Validated TCO form inputs (PIS-18).

    Server-side validation backs the React form checks — never trust the
    frontend alone. `lifecycle_years` is capped at 5: PIS-24 #5 forbids
    projections beyond a 5-year planning horizon.

    The six "additional cost" fields below were added in PID amendment 1.3 to
    model real refresh spend that the original three-input form understated
    (installation labor, accessories, spares, training, recurring support, and
    adjacent recurring contracts). All default to `0.0` — leaving a field at its
    default is an *explicit* user choice ("I have no cost here"), not a silent
    fill of a missing required input (Eval 4).

    `refresh_events` (PID amendment 1.5) models mid-cycle hardware refreshes
    inside the lifecycle window. The default is an empty list, so legacy saved
    scenarios deserialize unchanged.
    """

    model_config = ConfigDict(from_attributes=True)

    device_count: int = Field(..., gt=0, description="Number of network devices")
    hardware_cost_per_unit: float = Field(..., ge=0)
    licensing_cost_per_unit_year: float = Field(..., ge=0)
    support_cost_year_one: float = Field(default=0.0, ge=0)
    lifecycle_years: int = Field(default=5, ge=1, le=5)
    device_category: str = Field(default="access_point")

    # PID amendment 1.3 — additional cost categories. All Y1 one-time unless
    # noted; all optional with explicit $0 default.
    installation_cost: float = Field(
        default=0.0,
        ge=0,
        description="One-time Y1 professional services / install labor",
    )
    accessories_cost_per_unit: float = Field(
        default=0.0,
        ge=0,
        description="One-time Y1 per-device accessories (mounts, cables, optics)",
    )
    spares_percent: float = Field(
        default=0.0,
        ge=0,
        le=100,
        description="Spare units as a percentage of device_count (0-100); Y1 only",
    )
    training_cost: float = Field(
        default=0.0,
        ge=0,
        description="One-time Y1 migration / training labor",
    )
    support_cost_recurring_per_year: float = Field(
        default=0.0,
        ge=0,
        description="Recurring support contract from Y2 onward",
    )
    adjacent_recurring_cost_per_year: float = Field(
        default=0.0,
        ge=0,
        description="Adjacent existing-stack recurring (e.g. NAC); applies Y1-Y5",
    )

    # PID amendment 1.5 — mid-cycle hardware refreshes. Empty by default.
    refresh_events: list[RefreshEvent] = Field(
        default_factory=list,
        description="Mid-cycle hardware refresh events; empty = no refresh.",
    )


class YearCost(BaseModel):
    """A single year's cost breakdown in the TCO model (PIS-15).

    The six fields after `support` were added in PID amendment 1.3. They default
    to `0.0` so saved scenarios from before the amendment deserialize unchanged.
    `refresh_hardware` was added in PID amendment 1.5 with the same default,
    so the year-by-year breakdown column appears only when mid-cycle refresh is
    actually used.
    """

    model_config = ConfigDict(from_attributes=True)

    year: int
    hardware: float
    licensing: float
    support: float
    total: float
    installation: float = 0.0
    accessories: float = 0.0
    spares: float = 0.0
    training: float = 0.0
    support_recurring: float = 0.0
    adjacent_recurring: float = 0.0
    refresh_hardware: float = 0.0


class TCOResult(BaseModel):
    """TCO Agent -> Report handoff contract (PIS-15).

    `warnings` carries reasonableness flags (PIS-21) and cascade notices
    (PIS-20); it is never stripped before reaching the UI or the report.
    """

    model_config = ConfigDict(from_attributes=True)

    scenario_name: str
    inputs: TCOFormInputs
    year_by_year: list[YearCost]
    total_5yr: float
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class TCOScenarioCreate(BaseModel):
    """Inbound payload for computing / saving a TCO scenario.

    `parent_scenario_id` is the versioning hook (PID amendment 1.5). When set,
    the saved scenario inherits the parent's lineage and is stored as the next
    version in that lineage. When absent, the save starts a new lineage at v1.
    """

    scenario_name: str = Field(..., min_length=1, max_length=200)
    inputs: TCOFormInputs
    parent_scenario_id: str | None = Field(
        default=None,
        description=(
            "Optional id of an existing scenario to save this as a new version "
            "of. The new row inherits the parent's lineage_id and bumps version "
            "by 1."
        ),
    )


class TCOScenarioRead(BaseModel):
    """Outbound representation of a persisted TCO scenario.

    `lineage_id` groups successive versions of the same scenario; `version` is
    the 1-indexed position within that lineage (PID amendment 1.5).
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    scenario_name: str
    inputs: dict
    year_by_year: list[dict]
    total_5yr: float
    assumptions: list[str]
    warnings: list[str]
    created_at: datetime
    lineage_id: str
    version: int
