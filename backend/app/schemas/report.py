"""Pydantic schemas for report generation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ArtifactKind = Literal["tco", "comparison", "advisor_summary", "tco_comparison"]


class ReportArtifact(BaseModel):
    """A reference to one artifact to include in a report.

    `ref_id` is the saved TCO scenario / comparison id, or the conversation id
    for an advisor summary.

    For `tco_comparison` (PID amendment 1.5), `ref_id` holds the first scenario
    and `ref_id_b` holds the second; the renderer produces a side-by-side
    comparison. Both ids must be set and distinct.
    """

    kind: ArtifactKind
    ref_id: str = Field(..., min_length=1)
    ref_id_b: str | None = Field(
        default=None,
        description=(
            "Second TCO scenario id for `tco_comparison`. Required for that "
            "kind, ignored for every other kind."
        ),
    )

    @model_validator(mode="after")
    def _validate_pair(self) -> ReportArtifact:
        if self.kind == "tco_comparison":
            if not self.ref_id_b:
                raise ValueError("tco_comparison requires both ref_id and ref_id_b")
            if self.ref_id == self.ref_id_b:
                raise ValueError("tco_comparison requires two distinct scenarios")
        return self


class ReportRequest(BaseModel):
    """Inbound payload for `POST /projects/{id}/reports`.

    At least one artifact is required (PIS-05): a report must contain content.
    `artifacts` is capped so the renderer cannot be forced to assemble an
    unbounded document.
    """

    title: str = Field(..., min_length=1, max_length=200)
    artifacts: list[ReportArtifact] = Field(..., min_length=1, max_length=20)


class ReportRead(BaseModel):
    """Outbound metadata for a generated report."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    included_artifacts: list
    created_at: datetime
