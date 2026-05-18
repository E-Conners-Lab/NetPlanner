"""Advisor Agent (PIS-11, PIS-13).

Model: ``claude-sonnet-4-5`` — the only multi-turn agent. Streams a
business-decision-support response and invokes the Research Agent as an
on-demand tool (PIS-13). History is capped at 20 messages and the oldest 10
are summarized once it reaches 15 (PIS-16).

The spec anchor below is injected as the first system message on *every*
turn — not just at session start — to resist specification drift (PIS-17).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from app.schemas.conversation import MessageRead
from app.schemas.project import ProjectContext
from app.schemas.research import ResearchResult

# PIS-17 — hard anchor block. Injected first on every Advisor turn.
ADVISOR_SYSTEM_ANCHOR = (
    "You are NetPlanner's business advisor. Your role is exclusively business "
    "decision support for network infrastructure planning: TCO, vendor "
    "justification, budget narratives, and ROI framing. Do not provide "
    "configuration commands, remediation steps, network troubleshooting, or "
    "operational guidance. If asked for anything outside this scope, state "
    "your limitation clearly and refer the user to appropriate technical "
    "resources."
)


async def stream_advisor_turn(
    messages: list[MessageRead],
    project_context: ProjectContext,
    research_results: ResearchResult | None = None,
) -> AsyncGenerator[str, None]:
    """Stream one Advisor conversation turn as text chunks.

    Args:
        messages: Conversation history (capped/summarized per PIS-16).
        project_context: The project's structured context (PIS-15).
        research_results: Optional pricing context if Research was invoked.

    Yields:
        str: Response text chunks, framed as SSE ``data:`` events by the route.

    Raises:
        NotImplementedError: Always — implemented in Phase 2.
    """
    raise NotImplementedError("Advisor Agent — implemented in Phase 2")
    yield ""  # pragma: no cover — marks this coroutine as an async generator
