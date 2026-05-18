"""Pydantic schemas for report generation."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ArtifactKind = Literal["tco", "comparison", "advisor_summary"]


class ReportArtifact(BaseModel):
    """A reference to one artifact to include in a report.

    `ref_id` is the saved TCO scenario / comparison id, or the conversation id
    for an advisor summary.
    """

    kind: ArtifactKind
    ref_id: str = Field(..., min_length=1)


class ReportRequest(BaseModel):
    """Inbound payload for `POST /projects/{id}/reports`.

    At least one artifact is required (PIS-05): a report must contain content.
    """

    title: str = Field(..., min_length=1, max_length=200)
    artifacts: list[ReportArtifact] = Field(..., min_length=1)


class ReportRead(BaseModel):
    """Outbound metadata for a generated report."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    included_artifacts: list
    created_at: datetime
