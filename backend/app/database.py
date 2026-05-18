"""SQLAlchemy async engine, session factory, and the declarative Base.

The database is SQLite accessed through the async `aiosqlite` driver. Route
handlers obtain a session via the `get_db` dependency (FastAPI `Depends`).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

_settings = get_settings()


class Base(DeclarativeBase):
    """Declarative base for every ORM model in the project."""


def new_uuid() -> str:
    """Return a fresh UUID4 string — used for all primary keys."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class TimestampMixin:
    """Adds `created_at` / `updated_at` columns to a model.

    Kept here next to `Base` so every model shares one definition (DRY).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


# Async engine + session factory. `expire_on_commit=False` keeps ORM objects
# usable after commit, which matters for returning them from route handlers.
engine = create_async_engine(_settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Create all tables if they do not yet exist.

    Invoked from the FastAPI lifespan handler. Alembic owns schema *changes*;
    this is a convenience for first-run / development. It fails loud — a
    broken DB is a mandatory-dependency failure, not something to swallow.
    """
    # Import models so they register with `Base.metadata` before create_all.
    from app import models  # noqa: F401  (import for side effects)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a scoped async DB session.

    Rolls back on any exception so a failed request never leaves a partial
    transaction open, then always closes the session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
