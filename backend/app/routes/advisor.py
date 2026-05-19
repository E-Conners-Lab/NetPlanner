"""Advisor route — streaming conversational endpoint.

Responses are Server-Sent Events (`text/event-stream`). Each event is a JSON
payload: ``{"type": "token", "content": ...}`` for response chunks,
``{"type": "done", "conversation_id": ...}`` at the end, or
``{"type": "error", "content": ...}`` on failure.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.advisor import project_context_is_sufficient, stream_advisor_turn
from app.agents.project_context import build_project_context
from app.database import get_db
from app.models.conversation import Conversation
from app.schemas.conversation import AdvisorRequest, ConversationSummary
from app.services import conversation_service, project_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["advisor"])

# PIS-04 / Eval 7 — shown when a project lacks the context for grounded advice.
_CONTEXT_REQUEST = (
    "I need a bit more about this project before I can give grounded advice. "
    "Add a description and/or existing-infrastructure notes to the project, "
    "then ask again."
)
# SEC-24 — SSE responses carry session-bound data; never cache them.
_SSE_HEADERS = {"Cache-Control": "no-store"}


def _sse(payload: dict) -> str:
    """Frame a payload as one Server-Sent Event."""
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/{project_id}/advisor")
async def advisor_turn(
    project_id: str,
    payload: AdvisorRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream one Advisor conversation turn as SSE (PIS-13)."""
    project = await project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")

    context = await build_project_context(project)

    # Eval 7 / PIS-04: without project context, request it — do not answer.
    if not project_context_is_sufficient(context):

        async def _request_context() -> AsyncGenerator[str, None]:
            yield _sse({"type": "token", "content": _CONTEXT_REQUEST})
            yield _sse({"type": "done", "conversation_id": None})

        return StreamingResponse(
            _request_context(), media_type="text/event-stream", headers=_SSE_HEADERS
        )

    # Resolve the conversation and record the user's message.
    if payload.conversation_id:
        conversation = await conversation_service.get_conversation(
            db, payload.conversation_id
        )
        # SEC-27: verify the conversation belongs to this project.
        if conversation is None or conversation.project_id != project_id:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, detail="Conversation not found"
            )
    else:
        conversation = await conversation_service.create_conversation(db, project_id)

    await conversation_service.add_message(db, conversation.id, "user", payload.message)
    history = [
        {"role": m.role, "content": m.content}
        for m in await conversation_service.list_messages(db, conversation.id)
    ]
    conversation_id = conversation.id

    async def _advisor_stream() -> AsyncGenerator[str, None]:
        collected: list[str] = []
        try:
            async for chunk in stream_advisor_turn(history, context):
                collected.append(chunk)
                yield _sse({"type": "token", "content": chunk})
            await conversation_service.add_message(
                db, conversation_id, "assistant", "".join(collected)
            )
            yield _sse({"type": "done", "conversation_id": conversation_id})
        except Exception:
            # PIS-20: surface a generic error (SEC-11 — no internals leaked).
            logger.exception(
                "Advisor stream failed for conversation %s", conversation_id
            )
            yield _sse(
                {
                    "type": "error",
                    "content": "The advisor response failed. Please try again.",
                }
            )

    return StreamingResponse(
        _advisor_stream(), media_type="text/event-stream", headers=_SSE_HEADERS
    )


@router.get("/{project_id}/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> list[Conversation]:
    """List a project's Advisor conversations, newest first."""
    project = await project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found")
    return await conversation_service.list_conversations(db, project_id)
