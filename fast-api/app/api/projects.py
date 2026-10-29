from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status

from app.auth.dependencies import current_user
from app.core.config import settings
from app.db.core.projects_repository import (
    create_project,
    get_project,
    list_projects,
    soft_delete_project_with_revision,
    update_project_with_revision,
)
from app.db.models.projects import Project
from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectSettingsPayload,
    ProjectUpdateRequest,
)

router = APIRouter(prefix="/v1/projects", tags=["projects"])


def _etag_for_revision(revision: int) -> str:
    return f"\"{revision}\""


def _parse_if_match(value: str | None) -> int:
    if value is None:
        raise HTTPException(status_code=status.HTTP_428_PRECONDITION_REQUIRED, detail="If-Match header is required.")

    cleaned = value.strip()
    if cleaned.startswith("W/"):
        cleaned = cleaned[2:].strip()

    if len(cleaned) < 2 or not (cleaned.startswith("\"") and cleaned.endswith("\"")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="If-Match header must contain a quoted ETag revision.")

    revision_value = cleaned[1:-1].strip()
    if not revision_value.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="If-Match revision must be numeric.")

    revision = int(revision_value)
    if revision < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="If-Match revision must be greater than zero.")
    return revision


def _validate_cookie_origin(request: Request, authorization: str | None) -> None:
    is_bearer = bool(authorization and authorization.lower().startswith("bearer "))
    if is_bearer:
        return

    if settings.SESSION_COOKIE_NAME not in request.cookies:
        return

    origin = request.headers.get("origin")
    if origin is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin header is required for cookie-authenticated mutations.")

    normalized = origin.strip()
    if not normalized or normalized.lower() == "null":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin header is invalid.")

    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin header is malformed.")

    if normalized.rstrip("/") not in settings.TRUSTED_ORIGINS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin is not trusted.")


def _to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        projectType=project.project_type,
        settings=ProjectSettingsPayload(
            languages=list(project.languages),
            frameworks=list(project.frameworks),
            runtimes=list(project.runtimes),
            databaseCategories=list(project.database_categories),
        ),
        revision=project.revision,
        status=project.status,
        createdAt=project.created_at,
        updatedAt=project.updated_at,
    )


def _require_project(owner_id: str, project_id: str) -> Project:
    project = get_project(owner_id=owner_id, project_id=project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project_route(
    payload: ProjectCreateRequest,
    response: Response,
    request: Request,
    user: Annotated[dict[str, Any], Depends(current_user)],
    authorization: Annotated[str | None, Header()] = None,
) -> ProjectResponse:
    _validate_cookie_origin(request, authorization)

    project = create_project(
        owner_id=user["user_id"],
        actor_id=user["user_id"],
        name=payload.name.strip(),
        description=payload.description.strip(),
        project_type=payload.project_type,
        languages=payload.settings.languages,
        frameworks=payload.settings.frameworks,
        runtimes=payload.settings.runtimes,
        database_categories=payload.settings.database_categories,
    )

    response.headers["ETag"] = _etag_for_revision(project.revision)
    return _to_response(project)


@router.get("", response_model=ProjectListResponse)
async def list_projects_route(
    user: Annotated[dict[str, Any], Depends(current_user)],
    page: int = 1,
    page_size: int = 20,
) -> ProjectListResponse:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pagination parameters.")

    paginated = list_projects(owner_id=user["user_id"], page=page, page_size=page_size)
    return ProjectListResponse(
        items=[_to_response(item) for item in paginated.items],
        page=paginated.page,
        pageSize=paginated.page_size,
        total=paginated.total,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_route(
    project_id: str,
    response: Response,
    user: Annotated[dict[str, Any], Depends(current_user)],
) -> ProjectResponse:
    project = _require_project(user["user_id"], project_id)
    response.headers["ETag"] = _etag_for_revision(project.revision)
    return _to_response(project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project_route(
    project_id: str,
    payload: ProjectUpdateRequest,
    response: Response,
    request: Request,
    user: Annotated[dict[str, Any], Depends(current_user)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> ProjectResponse:
    _validate_cookie_origin(request, authorization)
    revision = _parse_if_match(if_match)

    updated = update_project_with_revision(
        owner_id=user["user_id"],
        actor_id=user["user_id"],
        project_id=project_id,
        current_revision=revision,
        name=payload.name.strip(),
        description=payload.description.strip(),
        project_type=payload.project_type,
        languages=payload.settings.languages,
        frameworks=payload.settings.frameworks,
        runtimes=payload.settings.runtimes,
        database_categories=payload.settings.database_categories,
    )
    if updated is None:
        existing = get_project(owner_id=user["user_id"], project_id=project_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="Project revision does not match If-Match.")

    response.headers["ETag"] = _etag_for_revision(updated.revision)
    return _to_response(updated)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_route(
    project_id: str,
    request: Request,
    user: Annotated[dict[str, Any], Depends(current_user)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    _validate_cookie_origin(request, authorization)
    revision = _parse_if_match(if_match)

    deleted = soft_delete_project_with_revision(
        owner_id=user["user_id"],
        actor_id=user["user_id"],
        project_id=project_id,
        current_revision=revision,
    )
    if deleted is None:
        existing = get_project(owner_id=user["user_id"], project_id=project_id)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail="Project revision does not match If-Match.")

    return Response(status_code=status.HTTP_204_NO_CONTENT)
