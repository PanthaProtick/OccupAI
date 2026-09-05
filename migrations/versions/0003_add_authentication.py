"""Add users and opaque authentication sessions."""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("normalized_email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("last_login_at", sa.String(), nullable=True),
        sa.CheckConstraint("role IN ('user','admin')", name="ck_users_role"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_users_name"))
    op.create_index("ix_users_normalized_email", "users", ["normalized_email"], unique=True)
    op.create_table("authentication_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=False),
        sa.Column("last_used_at", sa.String(), nullable=True),
        sa.Column("revoked_at", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"))
    op.create_index("ix_authentication_sessions_user_id", "authentication_sessions", ["user_id"])
    op.create_index("ix_authentication_sessions_token_hash", "authentication_sessions", ["token_hash"], unique=True)
    op.create_index("ix_authentication_sessions_expires_at", "authentication_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_table("authentication_sessions")
    op.drop_table("users")
