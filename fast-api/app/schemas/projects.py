from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.projects_catalog import (
    FRAMEWORK_LANGUAGE_COMPATIBILITY,
    RUNTIME_LANGUAGE_COMPATIBILITY,
    TECHNOLOGY_CATALOG,
)


def _unique_values(values: list[str]) -> list[str]:
    normalized = [value.strip().lower() for value in values if value and value.strip()]
    return list(dict.fromkeys(normalized))


def _validate_allowed(field_name: str, values: list[str], *, allowed: tuple[str, ...]) -> list[str]:
    invalid = sorted(set(values) - set(allowed))
    if invalid:
        raise ValueError(f"Unsupported {field_name}: {', '.join(invalid)}")
    return values


class ProjectSettingsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    languages: list[str] = Field(default_factory=list, min_length=1, max_length=16)
    frameworks: list[str] = Field(default_factory=list, max_length=16)
    runtimes: list[str] = Field(default_factory=list, max_length=16)
    database_categories: list[str] = Field(
        default_factory=list,
        max_length=16,
        alias="databaseCategories",
        serialization_alias="databaseCategories",
    )

    @model_validator(mode="after")
    def validate_catalog(self) -> "ProjectSettingsPayload":
        self.languages = _validate_allowed(
            "languages",
            _unique_values(self.languages),
            allowed=TECHNOLOGY_CATALOG["languages"],
        )
        self.frameworks = _validate_allowed(
            "frameworks",
            _unique_values(self.frameworks),
            allowed=TECHNOLOGY_CATALOG["frameworks"],
        )
        self.runtimes = _validate_allowed(
            "runtimes",
            _unique_values(self.runtimes),
            allowed=TECHNOLOGY_CATALOG["runtimes"],
        )
        self.database_categories = _validate_allowed(
            "database categories",
            _unique_values(self.database_categories),
            allowed=TECHNOLOGY_CATALOG["databaseCategories"],
        )

        language_set = set(self.languages)
        for framework in self.frameworks:
            supported_languages = set(FRAMEWORK_LANGUAGE_COMPATIBILITY.get(framework, ()))
            if supported_languages and language_set.isdisjoint(supported_languages):
                raise ValueError(f"Framework '{framework}' is incompatible with selected languages.")

        for runtime in self.runtimes:
            supported_languages = set(RUNTIME_LANGUAGE_COMPATIBILITY.get(runtime, ()))
            if supported_languages and language_set.isdisjoint(supported_languages):
                raise ValueError(f"Runtime '{runtime}' is incompatible with selected languages.")

        return self


class ProjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=4000)
    project_type: Literal["frontend", "backend", "fullstack", "general"] = Field(
        alias="projectType",
        serialization_alias="projectType",
    )
    settings: ProjectSettingsPayload


class ProjectUpdateRequest(ProjectCreateRequest):
    pass


class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    project_type: str = Field(alias="projectType", serialization_alias="projectType")
    settings: ProjectSettingsPayload
    revision: int
    status: str
    created_at: int = Field(alias="createdAt", serialization_alias="createdAt")
    updated_at: int = Field(alias="updatedAt", serialization_alias="updatedAt")


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ProjectResponse]
    page: int
    page_size: int = Field(alias="pageSize", serialization_alias="pageSize")
    total: int
