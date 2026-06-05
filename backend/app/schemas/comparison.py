"""Pydantic schemas for Vendor Comparison, including the Report handoff."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.research import Confidence


def _normalize_vendor(name: str) -> str:
    """Trim and collapse interior whitespace to one space."""
    return re.sub(r"\s+", " ", name).strip()


class ComparisonRequest(BaseModel):
    """Inbound payload for generating a vendor comparison.

    PIS-02 #4 scopes comparisons to 2-3 platforms. Vendor names are
    normalized (trim + collapse whitespace) and validated against the
    paste-error / duplicate cases that surfaced during demo walkthrough:
    field-1 containing two vendor names mashed together produced a row
    where vendor[1] was a substring of vendor[0].
    """

    # PIS-02 #4 caps comparisons at 2–3 platforms. The string-length and
    # criteria-count caps protect the prompt budget and the matrix layout
    # (PIS-14 / PIS-18).
    vendors: list[str] = Field(..., min_length=2, max_length=3)
    criteria: list[str] = Field(..., min_length=1, max_length=10)

    @field_validator("vendors")
    @classmethod
    def _validate_vendor_lengths(cls, vendors: list[str]) -> list[str]:
        # `_validate_vendors` below normalizes and uniques — this guards the
        # raw input length before that normalization.
        for v in vendors:
            if len(v) > 120:
                raise ValueError("Vendor name too long (120 character limit).")
        return vendors

    @field_validator("criteria")
    @classmethod
    def _validate_criterion_lengths(cls, criteria: list[str]) -> list[str]:
        for c in criteria:
            if len(c) > 200:
                raise ValueError("Criterion too long (200 character limit).")
        return criteria

    @field_validator("vendors")
    @classmethod
    def _validate_vendors(cls, vendors: list[str]) -> list[str]:
        normalized = [_normalize_vendor(v) for v in vendors]

        for v in normalized:
            if not v:
                raise ValueError("Vendor names cannot be empty.")

        seen: set[str] = set()
        for v in normalized:
            key = v.lower()
            if key in seen:
                raise ValueError(f"Duplicate vendor: {v!r}.")
            seen.add(key)

        # Substring containment catches the paste-error case where vendor[0]
        # is literally "Cisco 9300  Arista 720XP" and vendor[1] is
        # "Arista 720XP" — render-time `' vs '.join()` would produce a
        # malformed title. Treat that as bad input rather than rendering it.
        lowered = [v.lower() for v in normalized]
        for i, a in enumerate(lowered):
            for j, b in enumerate(lowered):
                if i != j and b in a and a != b:
                    raise ValueError(
                        f"Vendor {normalized[i]!r} contains another vendor "
                        f"({normalized[j]!r}) — likely a paste error."
                    )

        return normalized

    @field_validator("criteria")
    @classmethod
    def _validate_criteria(cls, criteria: list[str]) -> list[str]:
        normalized = [_normalize_vendor(c) for c in criteria]

        for c in normalized:
            if not c:
                raise ValueError("Criterion cannot be empty.")

        seen: set[str] = set()
        for c in normalized:
            key = c.lower()
            if key in seen:
                raise ValueError(f"Duplicate criterion: {c!r}.")
            seen.add(key)

        # Symmetric paste-error guard with `_validate_vendors`. A live
        # Riverbend Health run shipped a comparison whose first criterion read
        # "PricingCloud management depth and multi-site administration
        # experience" — two intended criteria mashed together. The matrix
        # rendered a confused row with all `unavailable` cells. Treat that as
        # bad input rather than rendering it.
        lowered = [c.lower() for c in normalized]
        for i, a in enumerate(lowered):
            for j, b in enumerate(lowered):
                if i != j and b in a and a != b:
                    raise ValueError(
                        f"Criterion {normalized[i]!r} contains another "
                        f"criterion ({normalized[j]!r}) — likely a paste error."
                    )

        return normalized


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
