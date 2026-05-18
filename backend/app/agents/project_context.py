"""Project Context Agent (PIS-11).

Reads a persisted Project record and produces the structured ProjectContext
handoff contract consumed by every downstream agent (PIS-15). The context is
rebuilt fresh from the database at session start — never carried across
conversations (PIS-16).

This is a deterministic mapping, not an LLM call: the "agent" boundary exists
so downstream agents depend on the stable ProjectContext contract rather than
the ORM model.
"""

from __future__ import annotations

from app.models.project import Project
from app.schemas.project import ProjectContext


async def build_project_context(project: Project) -> ProjectContext:
    """Map a Project ORM record to the ProjectContext handoff contract.

    Args:
        project: The persisted project record.

    Returns:
        ProjectContext: ``{name, company, description, existing_infra,
        budget_ceiling}`` per PIS-15.
    """
    return ProjectContext.model_validate(project)
