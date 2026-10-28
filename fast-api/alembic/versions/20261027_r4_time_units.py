"""Normalize field-specific epoch units without rewriting applied history."""
from alembic import op
import sqlalchemy as sa

revision = "20261027_r4_time_units"
down_revision = "20261027_action_claims"
branch_labels = None
depends_on = None

# Intentionally frozen migration policy; do not import mutable application helpers.
SECONDS = (946684800, 4102444800)
MILLISECONDS = (946684800000, 4102444800000)
FIELDS = {
    "users": ("ms", ("created_at", "updated_at")),
    "user_settings": ("ms", ("created_at", "updated_at", "last_seen_at")),
    "sessions": ("s", ("created_at", "last_seen_at", "expires_at")),
    "oauth_states": ("s", ("created_at", "expires_at")),
    "integration_oauth_states": ("s", ("created_at", "expires_at")),
    "pending_actions": ("s", ("created_at", "expires_at")),
    "user_integrations": ("s", ("connected_at", "updated_at", "token_expires_at")),
    "action_resolutions": ("s", ("created_at_s", "updated_at_s")),
    "projects": ("ms", ("created_at", "updated_at", "deleted_at")),
    "project_settings_versions": ("ms", ("created_at",)),
}


def upgrade():
    connection = op.get_bind()
    # Validate every non-null value before changing any data. Invalid fields
    # cause refusal without printing private values or updating earlier fields.
    for table, (unit, fields) in FIELDS.items():
        for field in fields:
            invalid = connection.execute(sa.text(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{field}" IS NOT NULL '
                f'AND NOT (("{field}" >= :s0 AND "{field}" < :s1) '
                f'OR ("{field}" >= :m0 AND "{field}" < :m1))'
            ), dict(s0=SECONDS[0], s1=SECONDS[1], m0=MILLISECONDS[0], m1=MILLISECONDS[1])).scalar_one()
            if invalid:
                raise RuntimeError(f"R4 timestamp preflight refused: {table}.{field}; review data before migration")
    for table, (unit, fields) in FIELDS.items():
        low, high = SECONDS if unit == "ms" else MILLISECONDS
        for field in fields:
            expression = f'"{field}" * 1000' if unit == "ms" else f'CAST(FLOOR("{field}" / 1000.0) AS BIGINT)'
            connection.execute(sa.text(
                f'UPDATE "{table}" SET "{field}" = {expression} WHERE "{field}" >= :low AND "{field}" < :high'
            ), dict(low=low, high=high))


def downgrade():
    raise RuntimeError("R4 unit normalization is irreversible: legacy source units cannot be reconstructed. Restore a reviewed backup instead.")
