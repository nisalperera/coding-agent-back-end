"""Harden project ownership and soft-delete integrity.

Revision ID: 20261029_projects_contract_hardening
Revises: 20261027_r4_time_units
"""

from alembic import op


revision = "20261029_projects_contract_hardening"
down_revision = "20261027_r4_time_units"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_foreign_key(
        "fk_projects_deleted_by_users",
        "projects",
        "users",
        ["deleted_by"],
        ["user_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_projects_deleted_state_consistency",
        "projects",
        "(status = 'active' AND deleted_at IS NULL AND deleted_by IS NULL) "
        "OR (status = 'deleted' AND deleted_at IS NOT NULL AND deleted_by IS NOT NULL)",
    )
    op.create_index(
        "ix_projects_owner_id_revision_status",
        "projects",
        ["owner_id", "id", "revision", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_projects_owner_id_revision_status", table_name="projects")
    op.drop_constraint("ck_projects_deleted_state_consistency", "projects", type_="check")
    op.drop_constraint("fk_projects_deleted_by_users", "projects", type_="foreignkey")
