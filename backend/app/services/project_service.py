"""Project data-access service.

Keeps SQLAlchemy queries out of the route handlers (clean architecture).
Functions return ORM objects or `None`/`bool`; HTTP concerns (status codes,
404s) are the route layer's responsibility.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create_project(db: AsyncSession, data: ProjectCreate) -> Project:
    """Persist a new project and return it."""
    project = Project(**data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def list_projects(db: AsyncSession) -> list[Project]:
    """Return all projects, newest first."""
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return list(result.scalars().all())


async def get_project(db: AsyncSession, project_id: str) -> Project | None:
    """Return a project by id, or `None` if it does not exist."""
    return await db.get(Project, project_id)


async def update_project(
    db: AsyncSession, project_id: str, data: ProjectUpdate
) -> Project | None:
    """Apply a partial update to a project.

    Only fields explicitly supplied by the caller are changed (`exclude_unset`)
    so a partial PUT never blanks out untouched fields. Returns `None` if the
    project does not exist.

    Note: assigning to ORM attributes is SQLAlchemy's persistence mechanism —
    the project-wide immutability rule targets DTOs/value objects, not the ORM
    identity map.
    """
    project = await db.get(Project, project_id)
    if project is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: str) -> bool:
    """Delete a project. Returns `True` if a row was removed, `False` if not found."""
    project = await db.get(Project, project_id)
    if project is None:
        return False

    await db.delete(project)
    await db.commit()
    return True
