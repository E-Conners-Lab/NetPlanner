"""Conversation persistence for the Advisor feature.

Advisor history is persistent in SQLite (PIS-25). This module is the
data-access layer — creating conversations, appending messages, and reading
history back. Context-window management (PIS-16) lives with the Advisor Agent,
which decides what slice of history to send to the model.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message

_DEFAULT_TITLE = "Untitled conversation"
_TITLE_MAX_LENGTH = 60


def derive_title_from_message(message: str) -> str:
    """Derive a short, human-readable conversation title from a user message.

    Prefers the first sentence (terminated by ``. ! ?`` or newline) when it
    fits within the title budget; otherwise truncates at the last word
    boundary inside the budget and appends a horizontal ellipsis. An empty
    or whitespace-only message falls back to ``"Untitled conversation"``.

    Used by the Advisor route when it creates a fresh conversation, so the
    Reports artifact picker never lists generic "Untitled conversation"
    rows for sessions that have a usable first message.
    """
    text = message.strip()
    if not text:
        return _DEFAULT_TITLE

    sentence_end = re.search(r"[.!?\n]", text)
    if sentence_end and sentence_end.start() <= _TITLE_MAX_LENGTH:
        # If the terminator is at the very end of the message (single-
        # sentence question/statement that fits the budget), keep the
        # whole message including its trailing punctuation. Only strip
        # when there's more text after the terminator (multi-sentence).
        rest = text[sentence_end.end() :].strip()
        if not rest and len(text) <= _TITLE_MAX_LENGTH:
            return text
        candidate = text[: sentence_end.start()].strip()
        if candidate:
            return candidate

    if len(text) <= _TITLE_MAX_LENGTH:
        return text

    truncated = text[:_TITLE_MAX_LENGTH].rsplit(" ", 1)[0]
    return (truncated or text[:_TITLE_MAX_LENGTH]).rstrip() + "…"


async def create_conversation(
    db: AsyncSession, project_id: str, title: str = _DEFAULT_TITLE
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


# PIS-16 — at this many stored messages, fold the oldest into a summary so the
# Advisor's system prompt stays inside the token budget on long sessions.
_SUMMARIZE_AT = 15
_SUMMARIZE_OLDEST_N = 10
# Hard cap on the per-summary text length (bytes). A summary is compressed
# context, not a verbatim transcript.
_SUMMARY_MAX_LENGTH = 1200


def _compress_messages(messages: list[Message]) -> str:
    """Build a deterministic plain-text summary of message bodies.

    PIS-16 names "summarize" — the operating decision here is to do that
    deterministically rather than by spending a model call. The summary
    captures the gist (role + truncated body, separated by sentences) and
    leaves the recent history intact so the model still has fresh detail. If
    summarization-via-LLM is wanted later, this is the swap-in point.
    """
    parts: list[str] = []
    for message in messages:
        prefix = "User" if message.role == "user" else "Advisor"
        body = " ".join(message.content.split())  # collapse whitespace
        # Cap each per-message contribution to keep the summary short.
        if len(body) > 240:
            body = body[:240].rsplit(" ", 1)[0] + "…"
        parts.append(f"{prefix}: {body}")
    blob = " | ".join(parts)
    if len(blob) > _SUMMARY_MAX_LENGTH:
        blob = blob[: _SUMMARY_MAX_LENGTH - 1].rsplit(" ", 1)[0] + "…"
    return blob


async def maybe_summarize_history(db: AsyncSession, conversation_id: str) -> None:
    """Implement PIS-16's context degradation strategy.

    Once a conversation crosses the threshold, fold the oldest messages into
    `Conversation.summary` and delete those rows. The Advisor agent embeds
    the summary into the system prompt on subsequent turns so context
    survives the trim. No-op when the conversation is under the threshold.
    """
    messages = await list_messages(db, conversation_id)
    if len(messages) < _SUMMARIZE_AT:
        return

    conversation = await get_conversation(db, conversation_id)
    if conversation is None:
        return

    oldest = messages[:_SUMMARIZE_OLDEST_N]
    compressed = _compress_messages(oldest)
    if conversation.summary:
        # Concatenate so we keep history of prior summaries within the cap.
        combined = f"{conversation.summary} | {compressed}"
        if len(combined) > _SUMMARY_MAX_LENGTH:
            combined = combined[: _SUMMARY_MAX_LENGTH - 1].rsplit(" ", 1)[0] + "…"
        conversation.summary = combined
    else:
        conversation.summary = compressed

    for message in oldest:
        await db.delete(message)
    await db.commit()
