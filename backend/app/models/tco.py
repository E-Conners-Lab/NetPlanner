"""TCOScenario ORM model — a saved Total Cost of Ownership model (PIS-25).

A scenario is persisted only on explicit user save; the calculation itself is
ephemeral. Computed fields are stored as JSON to match the TCO → Report
handoff contract (PIS-15) without a separate per-year table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project


class TCOScenario(Base, TimestampMixin):
    """A saved TCO scenario belonging to a project."""

    __tablename__ = "tco_scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scenario_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Raw form inputs as submitted (TCOFormInputs serialized).
    inputs: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # year_by_year: list of {year, hardware, licensing, support, total} (PIS-15).
    year_by_year: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    total_5yr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    assumptions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Reasonableness / cascade warnings surfaced to the UI (PIS-20, PIS-21).
    warnings: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    project: Mapped[Project] = relationship(back_populates="tco_scenarios")
