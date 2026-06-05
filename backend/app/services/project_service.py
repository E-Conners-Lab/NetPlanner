"""Project data-access service.

Keeps SQLAlchemy queries out of the route handlers (clean architecture).
Functions return ORM objects or `None`/`bool`; HTTP concerns (status codes,
404s) are the route layer's responsibility.

SEC-03 / SEC-27: every read and write is scoped to a specific owner so a
caller cannot see, modify, or delete another user's project — the
`owner_id` filter is the authorization check.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


async def create_project(
    db: AsyncSession, owner_id: str, data: ProjectCreate
) -> Project:
    """Persist a new project owned by the given user and return it."""
    project = Project(owner_id=owner_id, **data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def list_projects(db: AsyncSession, owner_id: str) -> list[Project]:
    """Return all projects owned by the user, newest first."""
    result = await db.execute(
        select(Project)
        .where(Project.owner_id == owner_id)
        .order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


async def get_project(
    db: AsyncSession, project_id: str, owner_id: str
) -> Project | None:
    """Return a project by id if it belongs to the user (SEC-27).

    Cross-user access returns ``None`` — the route layer renders that as a
    404 so we never confirm whether a project with that id exists in another
    account.
    """
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == owner_id)
    )
    return result.scalar_one_or_none()


async def update_project(
    db: AsyncSession, project_id: str, owner_id: str, data: ProjectUpdate
) -> Project | None:
    """Apply a partial update to a project owned by the user.

    Only fields explicitly supplied by the caller are changed (`exclude_unset`)
    so a partial PUT never blanks out untouched fields. Returns ``None`` if
    the project does not exist or belongs to another user.
    """
    project = await get_project(db, project_id, owner_id)
    if project is None:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: str, owner_id: str) -> bool:
    """Delete a project owned by the user. Returns True if a row was removed."""
    project = await get_project(db, project_id, owner_id)
    if project is None:
        return False

    await db.delete(project)
    await db.commit()
    return True
