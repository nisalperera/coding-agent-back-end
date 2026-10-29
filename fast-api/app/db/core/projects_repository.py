from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, func, insert, select, update

from app.db.base import current_time_ms
from app.db.database import db_session
from app.db.models.projects import Project, ProjectSettingsVersion


@dataclass(frozen=True)
class PaginatedProjects:
    items: list[Project]
    page: int
    page_size: int
    total: int


def _settings_payload(project: Project) -> dict[str, list[str]]:
    return {
        "languages": list(project.languages),
        "frameworks": list(project.frameworks),
        "runtimes": list(project.runtimes),
        "databaseCategories": list(project.database_categories),
    }


def create_project(
    *,
    owner_id: str,
    actor_id: str,
    name: str,
    description: str,
    project_type: str,
    languages: list[str],
    frameworks: list[str],
    runtimes: list[str],
    database_categories: list[str],
) -> Project:
    now = current_time_ms()

    with db_session() as session:
        project = Project(
            owner_id=owner_id,
            name=name,
            description=description,
            project_type=project_type,
            languages=list(languages),
            frameworks=list(frameworks),
            runtimes=list(runtimes),
            database_categories=list(database_categories),
            revision=1,
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(project)
        session.flush()

        session.add(
            ProjectSettingsVersion(
                project_id=project.id,
                revision=1,
                settings_json=_settings_payload(project),
                project_status=project.status,
                actor_id=actor_id,
                created_at=now,
            )
        )
        session.flush()
        session.refresh(project)
        return project


def list_projects(*, owner_id: str, page: int, page_size: int) -> PaginatedProjects:
    offset = (page - 1) * page_size

    with db_session() as session:
        base_filter = and_(Project.owner_id == owner_id, Project.status != "deleted")
        total = session.scalar(select(func.count()).select_from(Project).where(base_filter)) or 0

        items = list(
            session.scalars(
                select(Project)
                .where(base_filter)
                .order_by(Project.updated_at.desc(), Project.id.desc())
                .offset(offset)
                .limit(page_size)
            )
        )

        return PaginatedProjects(items=items, page=page, page_size=page_size, total=int(total))


def get_project(*, owner_id: str, project_id: str) -> Project | None:
    with db_session() as session:
        return session.scalar(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.owner_id == owner_id,
                    Project.status != "deleted",
                )
            )
        )


def update_project_with_revision(
    *,
    owner_id: str,
    actor_id: str,
    project_id: str,
    current_revision: int,
    name: str,
    description: str,
    project_type: str,
    languages: list[str],
    frameworks: list[str],
    runtimes: list[str],
    database_categories: list[str],
) -> Project | None:
    now = current_time_ms()
    next_revision = current_revision + 1

    with db_session() as session:
        update_result = session.execute(
            update(Project)
            .where(
                and_(
                    Project.id == project_id,
                    Project.owner_id == owner_id,
                    Project.revision == current_revision,
                    Project.status != "deleted",
                )
            )
            .values(
                name=name,
                description=description,
                project_type=project_type,
                languages=list(languages),
                frameworks=list(frameworks),
                runtimes=list(runtimes),
                database_categories=list(database_categories),
                revision=next_revision,
                updated_at=now,
            )
        )

        if update_result.rowcount != 1:
            return None

        session.execute(
            insert(ProjectSettingsVersion).values(
                project_id=project_id,
                revision=next_revision,
                settings_json={
                    "languages": list(languages),
                    "frameworks": list(frameworks),
                    "runtimes": list(runtimes),
                    "databaseCategories": list(database_categories),
                },
                project_status="active",
                actor_id=actor_id,
                created_at=now,
            )
        )

        return session.scalar(
            select(Project).where(and_(Project.id == project_id, Project.owner_id == owner_id))
        )


def soft_delete_project_with_revision(
    *,
    owner_id: str,
    actor_id: str,
    project_id: str,
    current_revision: int,
) -> Project | None:
    now = current_time_ms()
    next_revision = current_revision + 1

    with db_session() as session:
        update_result = session.execute(
            update(Project)
            .where(
                and_(
                    Project.id == project_id,
                    Project.owner_id == owner_id,
                    Project.revision == current_revision,
                    Project.status != "deleted",
                )
            )
            .values(
                status="deleted",
                revision=next_revision,
                deleted_at=now,
                deleted_by=actor_id,
                updated_at=now,
            )
        )

        if update_result.rowcount != 1:
            return None

        session.execute(
            insert(ProjectSettingsVersion).values(
                project_id=project_id,
                revision=next_revision,
                settings_json={},
                project_status="deleted",
                actor_id=actor_id,
                created_at=now,
            )
        )

        return session.scalar(
            select(Project).where(and_(Project.id == project_id, Project.owner_id == owner_id))
        )


def get_project_settings_versions_count(*, project_id: str) -> int:
    with db_session() as session:
        return int(
            session.scalar(
                select(func.count())
                .select_from(ProjectSettingsVersion)
                .where(ProjectSettingsVersion.project_id == project_id)
            )
            or 0
        )
