# Configuration Guide

## Environment variables

### Required for project mutation CSRF policy (cookie transport)

- `TRUSTED_ORIGINS`
  - Comma-separated absolute HTTP(S) origins.
  - Exact origin matching is enforced.
  - Missing/`null`/malformed/untrusted `Origin` headers are rejected for cookie-authenticated project mutations.

### Optional operator allowlist

- `OPERATOR_USER_IDS`
  - Comma-separated user IDs.
  - Empty value is default-deny (no operator users).
  - Operator access is deployment-controlled only; request payloads and user settings do not grant operator access.

## Authentication transport semantics

- ****** `Authorization: ****** accepted for project reads and mutations without `Origin` enforcement.
- Session cookie auth: accepted for project reads; project mutations require trusted `Origin`.

## Migration notes

- New Alembic revision: `20261029_projects_contract_hardening`
- Adds:
  - `projects.deleted_by -> users.user_id` foreign key
  - soft-delete consistency check constraint
  - CAS-supporting composite index on `projects(owner_id, id, revision, status)`
