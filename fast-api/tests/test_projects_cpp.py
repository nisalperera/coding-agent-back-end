import pytest
from pydantic import ValidationError

from app.schemas.projects import (
    ProjectCreateRequest,
    ProjectUpdateRequest,
)


def general_cpp_payload():
    return {
        "name": "C++ project",
        "description": "",
        "projectType": "general",
        "settings": {
            "languages": ["cpp"],
            "frameworks": [],
            "runtimes": [],
            "databaseCategories": [],
        },
    }


@pytest.mark.parametrize(
    "schema",
    [ProjectCreateRequest, ProjectUpdateRequest],
)
def test_general_cpp_project_is_accepted(schema):
    project = schema.model_validate(general_cpp_payload())

    assert project.project_type == "general"
    assert project.settings.languages == ["cpp"]
    assert project.settings.frameworks == []
    assert project.settings.runtimes == []


def test_unknown_language_is_still_rejected():
    payload = general_cpp_payload()
    payload["settings"]["languages"] = ["unknown-language"]

    with pytest.raises(ValidationError, match="Unsupported languages"):
        ProjectCreateRequest.model_validate(payload)


def test_cpp_does_not_bypass_framework_compatibility():
    payload = general_cpp_payload()
    payload["settings"]["frameworks"] = ["nextjs"]

    with pytest.raises(ValidationError, match="incompatible"):
        ProjectCreateRequest.model_validate(payload)


def test_cpp_does_not_bypass_runtime_compatibility():
    payload = general_cpp_payload()
    payload["settings"]["runtimes"] = ["node"]

    with pytest.raises(ValidationError, match="incompatible"):
        ProjectCreateRequest.model_validate(payload)
        