"""Conversation + Message ORM models for the Advisor feature.

Advisor history is per-session in memory and written to SQLite on session end
(PIS-25). `Conversation.summary` holds the compacted summary of the oldest
messages once history crosses the PIS-16 threshold.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project


class Conversation(Base, TimestampMixin):
    """A single Advisor conversation scoped to one project."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="Untitled conversation"
    )
    # Compacted summary of the oldest messages once history is summarized (PIS-16).
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped[Project] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base, TimestampMixin):
    """One turn in an Advisor conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # One of: "user", "assistant", "system".
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
