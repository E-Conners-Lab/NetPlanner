"""Unit tests for the Project Context Agent (PIS-11, PIS-15)."""

from __future__ import annotations

from app.agents.project_context import build_project_context
from app.models.project import Project
from app.schemas.project import ProjectContext


async def test_build_project_context_maps_all_fields() -> None:
    project = Project(
        name="Campus Wi-Fi Refresh",
        company="Acme Corp",
        description="Replace aging APs.",
        existing_infra="200 legacy APs.",
        budget_ceiling=250000.0,
    )

    context = await build_project_context(project)

    assert isinstance(context, ProjectContext)
    assert context.name == "Campus Wi-Fi Refresh"
    assert context.company == "Acme Corp"
    assert context.description == "Replace aging APs."
    assert context.existing_infra == "200 legacy APs."
    assert context.budget_ceiling == 250000.0


async def test_build_project_context_preserves_null_budget() -> None:
    # PIS-15: budget_ceiling is nullable — "no ceiling set" must not become 0.
    # String fields mirror a DB-loaded record (NOT NULL, default "").
    project = Project(
        name="No budget",
        company="",
        description="",
        existing_infra="",
        budget_ceiling=None,
    )

    context = await build_project_context(project)

    assert context.budget_ceiling is None
