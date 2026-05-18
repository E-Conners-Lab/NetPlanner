"""Report ORM model — metadata for a generated PDF export (PIS-22).

The PDF itself is a read-only file generation. This row records what was
included and when, so a project's export history is auditable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project


class Report(Base, TimestampMixin):
    """Metadata for one generated report export."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # included_artifacts: list of {kind, ref_id} describing what was exported.
    included_artifacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Filesystem path of the generated PDF, if retained after export.
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    project: Mapped[Project] = relationship(back_populates="reports")
