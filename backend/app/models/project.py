"""Project ORM model — the top-level planning scenario container (PIS-25)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.comparison import VendorComparison
    from app.models.conversation import Conversation
    from app.models.report import Report
    from app.models.tco import TCOScenario
    from app.models.user import User


class Project(Base, TimestampMixin):
    """A network planning project and the root of all saved artifacts.

    Maps to the Project Context handoff contract (PIS-15): name, company,
    description, existing_infra, budget_ceiling.
    """

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # SEC-03 / SEC-27: every persisted artifact is owned by a specific user.
    # The owner is enforced server-side on every read and write.
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    company: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    existing_infra: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Optional budget ceiling; null means "no ceiling set" (PIS-15).
    budget_ceiling: Mapped[float | None] = mapped_column(Float, nullable=True)

    owner: Mapped[User] = relationship(back_populates="projects")
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tco_scenarios: Mapped[list[TCOScenario]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    comparisons: Mapped[list[VendorComparison]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    reports: Mapped[list[Report]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
