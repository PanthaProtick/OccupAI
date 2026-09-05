"""Add persistent user notification preferences and notifications."""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("high_occupancy_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("high_occupancy_threshold", sa.Integer(), nullable=False, server_default="80"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.CheckConstraint(
            "high_occupancy_threshold BETWEEN 50 AND 100",
            name="ck_notification_preferences_threshold",
        ),
        sa.CheckConstraint("cooldown_minutes > 0", name="ck_notification_preferences_cooldown"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "user_notifications",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("room_id", sa.String(), nullable=True),
        sa.Column("suggested_room_id", sa.String(), nullable=True),
        sa.Column("occupancy_percentage", sa.Float(), nullable=True),
        sa.Column("deduplication_key", sa.String(255), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("read_at", sa.String(), nullable=True),
        sa.Column("dismissed_at", sa.String(), nullable=True),
        sa.Column("expires_at", sa.String(), nullable=True),
        sa.CheckConstraint("length(trim(type)) > 0", name="ck_user_notifications_type"),
        sa.CheckConstraint("length(trim(category)) > 0", name="ck_user_notifications_category"),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_user_notifications_title"),
        sa.CheckConstraint("length(trim(message)) > 0", name="ck_user_notifications_message"),
        sa.CheckConstraint(
            "occupancy_percentage IS NULL OR occupancy_percentage BETWEEN 0 AND 100",
            name="ck_user_notifications_occupancy_percentage",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.room_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["suggested_room_id"], ["rooms.room_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_notifications_user_id", "user_notifications", ["user_id"])
    op.create_index("ix_user_notifications_created_at", "user_notifications", ["created_at"])
    op.create_index("ix_user_notifications_read_at", "user_notifications", ["read_at"])
    op.create_index("ix_user_notifications_dismissed_at", "user_notifications", ["dismissed_at"])
    op.create_index(
        "ix_user_notifications_user_created", "user_notifications", ["user_id", "created_at"]
    )
    op.create_index(
        "ix_user_notifications_deduplication_key",
        "user_notifications",
        ["deduplication_key"],
    )


def downgrade() -> None:
    op.drop_table("user_notifications")
    op.drop_table("notification_preferences")
