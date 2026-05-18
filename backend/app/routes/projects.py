"""Project CRUD routes (Phase 1).

Thin handlers — data access lives in `app.services.project_service`. Errors
return a generic message (SEC-11); validation is enforced server-side by the
Pydantic request schemas (SEC-05).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])

_NOT_FOUND = "Project not found"

# Handlers return ORM `Project` objects; the `response_model=ProjectRead`
# on each route is the declared API contract and performs the conversion.


@router.get("", response_model=list[ProjectRead])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[Project]:
    """List all planning projects, newest first."""
    return await project_service.list_projects(db)


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, db: AsyncSession = Depends(get_db)
) -> Project:
    """Create a planning project."""
    return await project_service.create_project(db, payload)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)) -> Project:
    """Fetch a single project by id."""
    project = await project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)
) -> Project:
    """Apply a partial update to a project."""
    project = await project_service.update_project(db, project_id, payload)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str, db: AsyncSession = Depends(get_db)
) -> Response:
    """Delete a project.

    PIS-22 classifies this as a reversible write requiring a frontend
    confirmation dialog.
    """
    deleted = await project_service.delete_project(db, project_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=_NOT_FOUND)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
