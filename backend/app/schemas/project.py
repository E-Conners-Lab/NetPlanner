"""Pydantic schemas for Project CRUD and the Project Context handoff."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    """Fields shared by project create / read schemas."""

    name: str = Field(..., min_length=1, max_length=200)
    company: str = Field(default="", max_length=200)
    description: str = ""
    existing_infra: str = ""
    # Optional ceiling; must be non-negative when supplied (PIS-18).
    budget_ceiling: float | None = Field(default=None, ge=0)


class ProjectCreate(ProjectBase):
    """Inbound payload for `POST /projects`."""


class ProjectUpdate(BaseModel):
    """Inbound payload for `PUT /projects/{id}` — every field optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    description: str | None = None
    existing_infra: str | None = None
    budget_ceiling: float | None = Field(default=None, ge=0)


class ProjectRead(ProjectBase):
    """Outbound representation of a persisted project."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ProjectContext(BaseModel):
    """Project Context Agent -> all agents handoff contract (PIS-15).

    Re-injected fresh from the database at session start (PIS-16).
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    company: str
    description: str
    existing_infra: str
    budget_ceiling: float | None = None
