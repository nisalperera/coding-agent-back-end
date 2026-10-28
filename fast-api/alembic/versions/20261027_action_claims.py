"""Add retained approval-resolution ledger. No legacy action backfill."""
from alembic import op
import sqlalchemy as sa

revision = "20261027_action_claims"
down_revision = "7dd035aa729c"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "action_resolutions",
        sa.Column("action_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("claim_token", sa.String(36), nullable=False),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=True),
        sa.Column("created_at_s", sa.BigInteger(), nullable=False),
        sa.Column("updated_at_s", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("decision IN ('approve', 'deny')", name="ck_action_resolution_decision"),
        sa.CheckConstraint("state IN ('executing', 'denied', 'expired', 'succeeded', 'failed', 'uncertain')", name="ck_action_resolution_state"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("idx_action_resolutions_user_id", "action_resolutions", ["user_id"])


def downgrade():
    # Do not silently destroy deduplication or unresolved-write evidence.
    count = op.get_bind().execute(sa.text("SELECT count(*) FROM action_resolutions")).scalar_one()
    if count:
        raise RuntimeError("Refusing downgrade: retained action resolutions exist")
    op.drop_index("idx_action_resolutions_user_id", table_name="action_resolutions")
    op.drop_table("action_resolutions")
