"""Advisor route — streaming conversational endpoint.

Responses use Server-Sent Events (`text/event-stream`). The streaming plumbing
is wired in Phase 0; the Advisor Agent logic lands in Phase 2.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.conversation import AdvisorRequest

router = APIRouter(prefix="/projects", tags=["advisor"])


async def _placeholder_stream() -> AsyncGenerator[str, None]:
    """Emit a single SSE event until the Advisor Agent is implemented."""
    yield 'data: {"status": "not implemented"}\n\n'


@router.post("/{project_id}/advisor")
async def advisor_turn(
    project_id: str,
    payload: AdvisorRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream one Advisor conversation turn as SSE.

    Multi-turn agent per PIS-13. Agent logic implemented in Phase 2.
    """
    return StreamingResponse(_placeholder_stream(), media_type="text/event-stream")
