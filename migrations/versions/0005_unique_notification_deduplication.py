"""Make notification ingestion deduplication keys unique."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_user_notifications_deduplication_key", table_name="user_notifications")
    op.create_index(
        "ix_user_notifications_deduplication_key",
        "user_notifications",
        ["deduplication_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_user_notifications_deduplication_key", table_name="user_notifications")
    op.create_index(
        "ix_user_notifications_deduplication_key",
        "user_notifications",
        ["deduplication_key"],
        unique=False,
    )
