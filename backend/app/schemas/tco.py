"""Pydantic schemas for the TCO Calculator, including the Report handoff."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class YearCost(BaseModel):
    """A single year's cost breakdown in the TCO model (PIS-15).

    The six fields after `support` were added in PID amendment 1.3. They default
    to `0.0` so saved scenarios from before the amendment deserialize unchanged.
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
    """Inbound payload for computing / saving a TCO scenario."""

    scenario_name: str = Field(..., min_length=1, max_length=200)
    inputs: TCOFormInputs


class TCOScenarioRead(BaseModel):
    """Outbound representation of a persisted TCO scenario."""

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
