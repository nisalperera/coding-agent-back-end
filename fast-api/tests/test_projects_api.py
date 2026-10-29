from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.auth.dependencies import current_user
from app.core.config import settings
from app.db.core.projects_repository import get_project_settings_versions_count
from app.db.database import db_session
from app.db.models.common import User
from main import app

PRIMARY_USER = {
    "user_id": "77777777-7777-7777-7777-777777777777",
    "email": "projects-primary@example.test",
    "name": "Projects Primary",
}
SECONDARY_USER = {
    "user_id": "88888888-8888-8888-8888-888888888888",
    "email": "projects-secondary@example.test",
    "name": "Projects Secondary",
}


def _ensure_user(user: dict[str, str], sub: str) -> None:
    now = int(time.time())
    with db_session() as db:
        existing = db.scalar(select(User).where(User.user_id == user["user_id"]))
        if existing is None:
            db.add(
                User(
                    user_id=user["user_id"],
                    google_sub=sub,
                    email=user["email"],
                    email_verified=True,
                    name=user["name"],
                    picture=None,
                    created_at=now,
                    updated_at=now,
                )
            )


@pytest.fixture
def client() -> TestClient:
    _ensure_user(PRIMARY_USER, "projects-primary-sub")

    async def override_current_user() -> dict[str, str]:
        return PRIMARY_USER

    app.dependency_overrides[current_user] = override_current_user
    with TestClient(app, follow_redirects=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_payload() -> dict[str, object]:
    return {
        "name": "Acme API",
        "description": "Project description",
        "projectType": "backend",
        "settings": {
            "languages": ["python"],
            "frameworks": ["fastapi"],
            "runtimes": ["python"],
            "databaseCategories": ["sql"],
        },
    }


def test_project_create_requires_authentication() -> None:
    app.dependency_overrides.clear()
    with TestClient(app, follow_redirects=False) as unauthenticated_client:
        response = unauthenticated_client.post("/v1/projects", json=_create_payload())
    assert response.status_code in {401, 403}


def test_project_create_and_retrieve_emits_etag(client: TestClient) -> None:
    response = client.post("/v1/projects", json=_create_payload())
    assert response.status_code == 201, response.text
    assert response.headers["ETag"] == "\"1\""
    project_id = response.json()["id"]

    fetched = client.get(f"/v1/projects/{project_id}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.headers["ETag"] == "\"1\""
    assert fetched.json()["settings"]["frameworks"] == ["fastapi"]


def test_project_rejects_unknown_fields(client: TestClient) -> None:
    payload = _create_payload()
    payload["ownerId"] = PRIMARY_USER["user_id"]
    response = client.post("/v1/projects", json=payload)
    assert response.status_code == 422, response.text


def test_project_rejects_invalid_catalog_combinations(client: TestClient) -> None:
    payload = _create_payload()
    payload["settings"]["frameworks"] = ["react"]
    response = client.post("/v1/projects", json=payload)
    assert response.status_code == 422, response.text


def test_cookie_authenticated_mutation_requires_trusted_origin(client: TestClient) -> None:
    response = client.post(
        "/v1/projects",
        json=_create_payload(),
        cookies={settings.SESSION_COOKIE_NAME: "cookie-auth-token"},
    )
    assert response.status_code == 403, response.text


def test_bearer_authenticated_mutation_allows_missing_origin(client: TestClient) -> None:
    response = client.post(
        "/v1/projects",
        json=_create_payload(),
        headers={"Authorization": "******"},
    )
    assert response.status_code == 201, response.text


def test_project_list_excludes_soft_deleted_rows(client: TestClient) -> None:
    created = client.post("/v1/projects", json=_create_payload())
    project_id = created.json()["id"]
    assert client.delete(f"/v1/projects/{project_id}", headers={"If-Match": "\"1\""}).status_code == 204

    listed = client.get("/v1/projects")
    assert listed.status_code == 200, listed.text
    assert listed.json()["items"] == []


def test_project_update_requires_if_match(client: TestClient) -> None:
    created = client.post("/v1/projects", json=_create_payload())
    project_id = created.json()["id"]

    response = client.put(f"/v1/projects/{project_id}", json=_create_payload())
    assert response.status_code == 428, response.text


def test_project_update_rejects_stale_revision_without_orphan_versions(client: TestClient) -> None:
    created = client.post("/v1/projects", json=_create_payload())
    project_id = created.json()["id"]

    update_payload = _create_payload()
    update_payload["description"] = "Updated description"
    ok = client.put(
        f"/v1/projects/{project_id}",
        json=update_payload,
        headers={"If-Match": "\"1\""},
    )
    assert ok.status_code == 200, ok.text
    assert ok.headers["ETag"] == "\"2\""

    stale = client.put(
        f"/v1/projects/{project_id}",
        json=update_payload,
        headers={"If-Match": "\"1\""},
    )
    assert stale.status_code == 412, stale.text
    assert get_project_settings_versions_count(project_id=project_id) == 2


def test_project_owner_isolation_for_reads(client: TestClient) -> None:
    created = client.post("/v1/projects", json=_create_payload())
    project_id = created.json()["id"]

    _ensure_user(SECONDARY_USER, "projects-secondary-sub")

    async def override_secondary_user() -> dict[str, str]:
        return SECONDARY_USER

    app.dependency_overrides[current_user] = override_secondary_user
    with TestClient(app, follow_redirects=False) as secondary_client:
        response = secondary_client.get(f"/v1/projects/{project_id}")
        assert response.status_code == 404, response.text
