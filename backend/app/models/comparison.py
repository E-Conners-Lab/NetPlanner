"""VendorComparison ORM model — a saved vendor comparison matrix (PIS-25).

Persisted only on explicit user save. The matrix is stored as JSON matching
the Comparison → Report handoff contract (PIS-15): each cell carries a value,
source, and confidence indicator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project


class VendorComparison(Base, TimestampMixin):
    """A saved vendor comparison belonging to a project."""

    __tablename__ = "vendor_comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # vendors: list[str] (2-3 platforms per PIS-02 #4).
    vendors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # criteria: list[str].
    criteria: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # matrix: {vendor: {criterion: {value, source, confidence}}} (PIS-15).
    matrix: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    project: Mapped[Project] = relationship(back_populates="comparisons")
