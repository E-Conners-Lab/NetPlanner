"""Comparison Agent (PIS-11).

Model: ``claude-sonnet-4-5`` — multi-vendor synthesis with sourced data
(PIS-29). Builds a comparison matrix across 2-3 vendors and the user's
criteria, propagating ``source`` and ``confidence`` into every cell — never
stripping them (PIS-18, PIS-24 #1).
"""

from __future__ import annotations

from app.schemas.comparison import ComparisonResult
from app.schemas.project import ProjectContext
from app.schemas.research import ResearchResult


async def run_comparison_agent(
    vendors: list[str],
    criteria: list[str],
    research_data: ResearchResult,
    project_context: ProjectContext,
) -> ComparisonResult:
    """Produce a vendor comparison matrix.

    Args:
        vendors: 2-3 platform names to compare (PIS-02 #4).
        criteria: Evaluation criteria, one row per criterion.
        research_data: Live pricing context from the Research Agent.
        project_context: The project's structured context (PIS-15).

    Returns:
        ComparisonResult: The Comparison -> Report handoff contract — a matrix
        of confidence-tagged cells plus a narrative summary.

    Raises:
        NotImplementedError: Always — implemented in Phase 4.
    """
    raise NotImplementedError("Comparison Agent — implemented in Phase 4")
