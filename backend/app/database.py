"""SQLAlchemy async engine, session factory, and the declarative Base.

The database is SQLite accessed through the async `aiosqlite` driver. Route
handlers obtain a session via the `get_db` dependency (FastAPI `Depends`).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import DateTime, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

logger = logging.getLogger(__name__)

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


def _alembic_head_revision() -> str:
    """Read the head revision from the migration tree (no DB hit)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(cfg)
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("Alembic has no head revision")
    return head


async def _current_db_revision() -> str | None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        )
        row = result.first()
    return row[0] if row else None


async def init_db() -> None:
    """Initialize the database on startup.

    Production behavior (`environment == "production"`): the migration head
    must already be applied. We **never** silently fall back to
    `create_all()` in production — that is a footgun (schemas drift, indexes
    missing, alembic_version unwritten, future migrations break). Fail loud
    if the operator has not run ``alembic upgrade head``.

    Development behavior: tolerant first-run. If the database has no
    `alembic_version` table at all we boot with `create_all()` so a fresh
    `docker compose up` works without a migration step; if the table exists
    but lags head we fail with a clear remediation message.
    """
    # Import models so they register with `Base.metadata` before any usage.
    from app import models  # noqa: F401  (import for side effects)

    expected_head = _alembic_head_revision()
    try:
        current = await _current_db_revision()
    except Exception:  # alembic_version table does not exist yet
        current = None

    is_production = _settings.environment == "production"

    if current is None:
        if is_production:
            raise RuntimeError(
                "Database has not been initialized. Run "
                "`alembic upgrade head` before starting the app."
            )
        logger.warning(
            "init_db: no alembic_version found — creating schema directly "
            "for development. Run `alembic upgrade head` to manage schema "
            "via migrations."
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return

    if current != expected_head:
        message = (
            f"Database revision {current!r} is not at head {expected_head!r}. "
            f"Run `alembic upgrade head` before starting the app."
        )
        if is_production:
            raise RuntimeError(message)
        logger.error(message)
        raise RuntimeError(message)


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
