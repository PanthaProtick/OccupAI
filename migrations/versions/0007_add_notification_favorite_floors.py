"""Add user-selected upper floors to notification preferences."""

from alembic import op
import sqlalchemy as sa


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch:
        batch.add_column(sa.Column(
            "favorite_floors",
            sa.Text(),
            nullable=False,
            server_default="[]",
        ))


def downgrade() -> None:
    with op.batch_alter_table("notification_preferences") as batch:
        batch.drop_column("favorite_floors")
