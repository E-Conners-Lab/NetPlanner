"""Research Agent handoff contract (PIS-15).

Defined in its own module because the contract is consumed by three agents
(TCO, Comparison, Advisor) — a single source of truth avoids drift (DRY).
`Confidence` is the canonical pricing-confidence type used project-wide.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Canonical confidence type. Never a plain string (PIS-18, PIS-24 #1).
Confidence = Literal["confirmed", "estimated", "unavailable"]


class ResearchItem(BaseModel):
    """A single sourced pricing data point returned by the Research Agent.

    `confidence` defaults to `unavailable` — PIS-18 mandates that missing
    data is never silently treated as an assumed value.
    """

    model_config = ConfigDict(from_attributes=True)

    vendor: str
    product: str
    price_point: str
    unit: str
    source_url: str = ""
    confidence: Confidence = "unavailable"


class ResearchResult(BaseModel):
    """Research Agent -> TCO / Comparison / Advisor handoff contract (PIS-15).

    Results are capped at 3 per query (PIS-14 / PIS-26 retrieval strategy).
    """

    model_config = ConfigDict(from_attributes=True)

    query: str
    results: list[ResearchItem] = Field(default_factory=list, max_length=3)
