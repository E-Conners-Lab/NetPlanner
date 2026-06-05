"""Report ORM model — metadata for a generated PDF export (PIS-22).

The PDF itself is generated and stored as an **immutable snapshot** at create
time so a re-download returns the original artifact even if the underlying
TCO scenarios or comparisons have been edited or deleted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project


class Report(Base, TimestampMixin):
    """Metadata + immutable PDF snapshot for one generated report export."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # included_artifacts: list of {kind, ref_id} describing what was exported.
    included_artifacts: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Filesystem path of the generated PDF — used when `pdf_blob` is None and
    # the snapshot was streamed to disk (large-report fallback).
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Immutable PDF snapshot — bytes returned verbatim on re-download.
    pdf_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    project: Mapped[Project] = relationship(back_populates="reports")
