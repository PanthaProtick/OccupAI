"""Add durable, sampling-independent ingestion idempotency receipts."""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingestion_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.String(), nullable=False),
        sa.Column("observed_at", sa.String(), nullable=False),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("accepted_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["camera_id"], ["cameras.camera_id"], onupdate="CASCADE", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("camera_id", "observed_at", name="uq_receipts_camera_observed"),
        sa.UniqueConstraint("camera_id", "source_event_id", name="uq_receipts_camera_event"),
    )
    op.create_index("ix_ingestion_receipts_observed_at", "ingestion_receipts", ["observed_at"])


def downgrade() -> None:
    op.drop_index("ix_ingestion_receipts_observed_at", table_name="ingestion_receipts")
    op.drop_table("ingestion_receipts")
