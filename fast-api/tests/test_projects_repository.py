from __future__ import annotations

import threading
import time

from sqlalchemy import select

from app.db.core.projects_repository import (
    create_project,
    get_project,
    get_project_settings_versions_count,
    soft_delete_project_with_revision,
    update_project_with_revision,
)
from app.db.database import db_session
from app.db.models.common import User
from app.db.models.projects import Project

OWNER_ID = "99999999-9999-9999-9999-999999999999"


def _ensure_owner() -> None:
    now = int(time.time())
    with db_session() as db:
        existing = db.scalar(select(User).where(User.user_id == OWNER_ID))
        if existing is None:
            db.add(
                User(
                    user_id=OWNER_ID,
                    google_sub="projects-owner-sub",
                    email="projects-owner@example.test",
                    email_verified=True,
                    name="Projects Owner",
                    picture=None,
                    created_at=now,
                    updated_at=now,
                )
            )


def _create_project() -> Project:
    _ensure_owner()
    return create_project(
        owner_id=OWNER_ID,
        actor_id=OWNER_ID,
        name="Concurrent API",
        description="Concurrent updates",
        project_type="backend",
        languages=["python"],
        frameworks=["fastapi"],
        runtimes=["python"],
        database_categories=["sql"],
    )


def test_update_project_compare_and_swap_allows_only_one_winner() -> None:
    project = _create_project()
    winner_count = 0
    lock = threading.Lock()
    started = threading.Barrier(2)

    def worker(next_description: str) -> None:
        nonlocal winner_count
        started.wait()
        updated = update_project_with_revision(
            owner_id=OWNER_ID,
            actor_id=OWNER_ID,
            project_id=project.id,
            current_revision=1,
            name="Concurrent API",
            description=next_description,
            project_type="backend",
            languages=["python"],
            frameworks=["fastapi"],
            runtimes=["python"],
            database_categories=["sql"],
        )
        if updated is not None:
            with lock:
                winner_count += 1

    first = threading.Thread(target=worker, args=("description-1",))
    second = threading.Thread(target=worker, args=("description-2",))
    first.start()
    second.start()
    first.join()
    second.join()

    assert winner_count == 1
    latest = get_project(owner_id=OWNER_ID, project_id=project.id)
    assert latest is not None
    assert latest.revision == 2
    assert get_project_settings_versions_count(project_id=project.id) == 2


def test_soft_delete_uses_revision_precondition_and_hides_row() -> None:
    project = _create_project()

    deleted = soft_delete_project_with_revision(
        owner_id=OWNER_ID,
        actor_id=OWNER_ID,
        project_id=project.id,
        current_revision=1,
    )
    assert deleted is not None
    assert deleted.status == "deleted"

    stale_delete = soft_delete_project_with_revision(
        owner_id=OWNER_ID,
        actor_id=OWNER_ID,
        project_id=project.id,
        current_revision=1,
    )
    assert stale_delete is None
    assert get_project(owner_id=OWNER_ID, project_id=project.id) is None
    assert get_project_settings_versions_count(project_id=project.id) == 2
