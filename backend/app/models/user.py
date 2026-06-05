"""User ORM model — the identity record for the auth layer (SEC-02 / SEC-03).

NetPlanner is a single-tenant tool, but every persisted artifact is scoped to
the authenticated user so the app can safely run with more than one operator
on the same instance. Passwords are stored as Argon2id hashes (SEC-17) and are
never returned by any route.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project


class User(Base, TimestampMixin):
    """A registered user. Owns every project (and every project-scoped artifact)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # Email is the natural login key. Stored normalized (lowercased / stripped).
    email: Mapped[str] = mapped_column(
        String(254), nullable=False, unique=True, index=True
    )
    # Argon2id hash (SEC-17). The raw password is never persisted.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Bumped on logout / password change so prior JWTs stop validating —
    # logout becomes a real server-side invalidation (SEC-16).
    session_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Brute-force defense (SEC-06): consecutive failed logins, and the time
    # until which the account is locked. Reset to 0 / None on a successful
    # login. ``locked_until`` in the future means every login is rejected.
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    projects: Mapped[list[Project]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
