# coding-agent-back-end

FastAPI backend for coding-agent.

## Projects API (feature/projects-and-general-settings)

- Endpoints: `POST /v1/projects`, `GET /v1/projects`, `GET /v1/projects/{id}`, `PUT /v1/projects/{id}`, `DELETE /v1/projects/{id}`
- Ownership: every read/write is scoped to the authenticated user; owner identity is never accepted from request payloads.
- Concurrency control: mutation endpoints use revision ETags (`ETag: "<revision>"`) and require `If-Match` for update/delete.
- Soft delete: deleted projects are excluded from normal list/retrieve operations.
- Immutable history: every create/update/delete writes a `project_settings_versions` revision record in the same transaction.

## Authentication transport behavior

- ****** `Authorization: ****** is accepted for reads and mutations.
- Cookie authentication: when using the session cookie for project **mutations**, requests must include an exact trusted `Origin`.

## New configuration

- `TRUSTED_ORIGINS` (comma-separated absolute origins; exact match only, no wildcards/suffix matching)
- `OPERATOR_USER_IDS` (comma-separated user IDs; empty by default which denies all operator access)

See `config_guide.md` and `fast-api/.env.example` for full setup details.