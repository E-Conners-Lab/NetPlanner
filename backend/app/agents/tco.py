"""TCO Agent (PIS-11).

Model: ``claude-sonnet-4-5`` — structured math reasoning plus narrative output
(PIS-29). Builds a year-by-year cost model from validated form inputs.

Reasonableness check (PIS-21): if per-unit hardware cost falls below $50, or
per-unit annual licensing below $20, a warning is surfaced before the model is
considered complete — this is the Eval 6 silent-failure guard.
"""

from __future__ import annotations

from app.schemas.project import ProjectContext
from app.schemas.research import ResearchResult
from app.schemas.tco import TCOFormInputs, TCOResult


async def run_tco_agent(
    form_inputs: TCOFormInputs,
    research_data: ResearchResult,
    project_context: ProjectContext,
) -> TCOResult:
    """Produce a year-by-year TCO model for a set of form inputs.

    Args:
        form_inputs: Validated TCO form inputs.
        research_data: Live pricing context from the Research Agent. On
            research failure this is ``{results: []}`` and the model proceeds
            with visible warning flags (PIS-20) rather than failing silently.
        project_context: The project's structured context (PIS-15).

    Returns:
        TCOResult: The TCO -> Report handoff contract, including any
        reasonableness ``warnings`` (PIS-21).

    Raises:
        NotImplementedError: Always — implemented in Phase 3.
    """
    raise NotImplementedError("TCO Agent — implemented in Phase 3")
