"""Pydantic schemas for the TCO Calculator, including the Report handoff."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TCOFormInputs(BaseModel):
    """Validated TCO form inputs (PIS-18).

    Server-side validation backs the React form checks — never trust the
    frontend alone. `lifecycle_years` is capped at 5: PIS-24 #5 forbids
    projections beyond a 5-year planning horizon.
    """

    model_config = ConfigDict(from_attributes=True)

    device_count: int = Field(..., gt=0, description="Number of network devices")
    hardware_cost_per_unit: float = Field(..., ge=0)
    licensing_cost_per_unit_year: float = Field(..., ge=0)
    support_cost_year_one: float = Field(default=0.0, ge=0)
    lifecycle_years: int = Field(default=5, ge=1, le=5)
    device_category: str = Field(default="access_point")


class YearCost(BaseModel):
    """A single year's cost breakdown in the TCO model (PIS-15)."""

    model_config = ConfigDict(from_attributes=True)

    year: int
    hardware: float
    licensing: float
    support: float
    total: float


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
