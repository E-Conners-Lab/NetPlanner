"""Pydantic schemas for Vendor Comparison, including the Report handoff."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.research import Confidence


class ComparisonRequest(BaseModel):
    """Inbound payload for generating a vendor comparison.

    PIS-02 #4 scopes comparisons to 2-3 platforms.
    """

    vendors: list[str] = Field(..., min_length=2, max_length=3)
    criteria: list[str] = Field(..., min_length=1)


class ComparisonCell(BaseModel):
    """One cell in the comparison matrix — a sourced, confidence-tagged value.

    `confidence` defaults to `unavailable` so an unsourced cell is never
    presented as confirmed (PIS-24 #1).
    """

    model_config = ConfigDict(from_attributes=True)

    value: str
    source: str = ""
    confidence: Confidence = "unavailable"


class ComparisonResult(BaseModel):
    """Comparison Agent -> Report handoff contract (PIS-15).

    `matrix` is keyed `{vendor: {criterion: ComparisonCell}}`.
    """

    model_config = ConfigDict(from_attributes=True)

    vendors: list[str]
    criteria: list[str]
    matrix: dict[str, dict[str, ComparisonCell]]
    summary: str


class VendorComparisonRead(BaseModel):
    """Outbound representation of a persisted vendor comparison."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    vendors: list[str]
    criteria: list[str]
    matrix: dict
    summary: str
    created_at: datetime
