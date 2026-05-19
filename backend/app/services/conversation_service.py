"""Conversation persistence for the Advisor feature.

Advisor history is persistent in SQLite (PIS-25). This module is the
data-access layer — creating conversations, appending messages, and reading
history back. Context-window management (PIS-16) lives with the Advisor Agent,
which decides what slice of history to send to the model.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message


async def create_conversation(
    db: AsyncSession, project_id: str, title: str = "Untitled conversation"
) -> Conversation:
    """Create and persist a new conversation for a project."""
    conversation = Conversation(project_id=project_id, title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation(
    db: AsyncSession, conversation_id: str
) -> Conversation | None:
    """Return a conversation by id, or ``None`` if it does not exist."""
    return await db.get(Conversation, conversation_id)


async def list_conversations(db: AsyncSession, project_id: str) -> list[Conversation]:
    """Return a project's conversations, newest first."""
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


async def list_messages(db: AsyncSession, conversation_id: str) -> list[Message]:
    """Return a conversation's messages in chronological order."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession, conversation_id: str, role: str, content: str
) -> Message:
    """Append a message to a conversation and persist it."""
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message
