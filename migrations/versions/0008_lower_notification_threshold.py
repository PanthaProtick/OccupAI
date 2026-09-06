"""Lower the supported high-occupancy notification threshold to 45 percent."""

from alembic import op
import sqlalchemy as sa


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch:
        batch.drop_constraint("ck_notification_preferences_threshold", type_="check")
        batch.create_check_constraint(
            "ck_notification_preferences_threshold",
            "high_occupancy_threshold BETWEEN 45 AND 100",
        )
        batch.alter_column(
            "high_occupancy_threshold",
            existing_type=sa.Integer(),
            server_default="45",
            existing_nullable=False,
        )
    # Move only accounts still using the former default. Explicit custom
    # thresholds remain untouched.
    op.execute(
        "UPDATE notification_preferences "
        "SET high_occupancy_threshold = 45 "
        "WHERE high_occupancy_threshold = 80"
    )


def downgrade() -> None:
    # Values below the former constraint must be made valid before rebuilding it.
    op.execute(
        "UPDATE notification_preferences "
        "SET high_occupancy_threshold = 80 "
        "WHERE high_occupancy_threshold < 50"
    )
    with op.batch_alter_table("notification_preferences") as batch:
        batch.drop_constraint("ck_notification_preferences_threshold", type_="check")
        batch.create_check_constraint(
            "ck_notification_preferences_threshold",
            "high_occupancy_threshold BETWEEN 50 AND 100",
        )
        batch.alter_column(
            "high_occupancy_threshold",
            existing_type=sa.Integer(),
            server_default="80",
            existing_nullable=False,
        )
