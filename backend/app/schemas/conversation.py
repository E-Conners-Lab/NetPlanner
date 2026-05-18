"""Pydantic schemas for the Advisor conversation feature."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MessageRole = Literal["user", "assistant", "system"]


class MessageBase(BaseModel):
    """Fields shared by message create / read schemas."""

    role: MessageRole
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    """Inbound payload for appending a message to a conversation."""


class MessageRead(MessageBase):
    """Outbound representation of a persisted message."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    created_at: datetime


class ConversationRead(BaseModel):
    """Outbound representation of a conversation and its messages."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    title: str
    summary: str | None = None
    created_at: datetime
    messages: list[MessageRead] = Field(default_factory=list)


class AdvisorRequest(BaseModel):
    """Inbound payload for a single streaming Advisor turn.

    `conversation_id` is null to start a new conversation, set to continue one.
    """

    message: str = Field(..., min_length=1)
    conversation_id: str | None = None
