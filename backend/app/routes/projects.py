"""Project CRUD routes (Phase 1).

Thin handlers — data access lives in `app.services.project_service`. Errors
return a generic message (SEC-11); validation is enforced server-side by the
Pydantic request schemas (SEC-05). Every route requires authentication and
scopes the query to the authenticated user (SEC-02 / SEC-03 / SEC-27).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])

_NOT_FOUND = "Project not found"


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Project]:
    """List the authenticated user's planning projects, newest first."""
    return await project_service.list_projects(db, user.id)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """Create a planning project owned by the authenticated user."""
    return await project_service.create_project(db, user.id, payload)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """Fetch one of the user's projects by id."""
    project = await project_service.get_project(db, project_id, user.id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """Apply a partial update to one of the user's projects."""
    project = await project_service.update_project(db, project_id, user.id, payload)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    """Delete one of the user's projects.

    PIS-22 classifies this as a reversible write requiring a frontend
    confirmation dialog.
    """
    deleted = await project_service.delete_project(db, project_id, user.id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
