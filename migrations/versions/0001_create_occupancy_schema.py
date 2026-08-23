"""Create the immutable initial OccupAI SQLite schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rooms",
        sa.Column("room_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("building", sa.String(), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("behavior_profile", sa.String(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_rooms_name"),
        sa.CheckConstraint("capacity > 0", name="ck_rooms_capacity"),
        sa.CheckConstraint("length(trim(building)) > 0", name="ck_rooms_building"),
        sa.CheckConstraint("floor >= 0", name="ck_rooms_floor"),
        sa.CheckConstraint("length(trim(behavior_profile)) > 0", name="ck_rooms_profile"),
    )
    op.create_table(
        "cameras",
        sa.Column("camera_id", sa.String(), primary_key=True),
        sa.Column("room_id", sa.String(), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("stale_after_seconds", sa.Float(), nullable=False, server_default="10"),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.room_id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("enabled IN (0, 1)", name="ck_cameras_enabled"),
        sa.CheckConstraint("stale_after_seconds > 0", name="ck_cameras_stale_after"),
    )
    op.create_table(
        "camera_states",
        sa.Column("camera_id", sa.String(), primary_key=True),
        sa.Column("raw_occupancy", sa.Integer(), nullable=True),
        sa.Column("occupancy", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("observed_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.Column("diagnostics_json", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"], onupdate="CASCADE", ondelete="CASCADE"),
        sa.CheckConstraint("raw_occupancy IS NULL OR raw_occupancy >= 0", name="ck_states_raw"),
        sa.CheckConstraint("occupancy IS NULL OR occupancy >= 0", name="ck_states_occupancy"),
        sa.CheckConstraint("status IN ('online','stale','offline')", name="ck_states_status"),
    )
    op.create_table(
        "occupancy_samples",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("camera_id", sa.String(), nullable=False),
        sa.Column("observed_at", sa.String(), nullable=False),
        sa.Column("raw_occupancy", sa.Integer(), nullable=False),
        sa.Column("occupancy", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("capacity_snapshot", sa.Integer(), nullable=False),
        sa.Column("source_sequence", sa.Integer(), nullable=True),
        sa.Column("source_event_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.UniqueConstraint("camera_id", "observed_at", name="uq_samples_camera_observed"),
        sa.UniqueConstraint("camera_id", "source_event_id", name="uq_samples_camera_event"),
        sa.CheckConstraint("raw_occupancy >= 0", name="ck_samples_raw"),
        sa.CheckConstraint("occupancy >= 0", name="ck_samples_occupancy"),
        sa.CheckConstraint("status IN ('online','stale')", name="ck_samples_status"),
        sa.CheckConstraint("capacity_snapshot > 0", name="ck_samples_capacity"),
    )
    op.create_index("ix_occupancy_samples_camera_time", "occupancy_samples", ["camera_id", "observed_at"])
    op.create_index("ix_occupancy_samples_observed_at", "occupancy_samples", ["observed_at"])
    op.create_table(
        "occupancy_buckets_5m",
        sa.Column("camera_id", sa.String(), primary_key=True),
        sa.Column("bucket_start", sa.String(), primary_key=True),
        sa.Column("avg_occupancy", sa.Float(), nullable=False),
        sa.Column("min_occupancy", sa.Integer(), nullable=False),
        sa.Column("max_occupancy", sa.Integer(), nullable=False),
        sa.Column("capacity_snapshot", sa.Integer(), nullable=False),
        sa.Column("coverage_percentage", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("expected_sample_count", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.camera_id"], onupdate="CASCADE", ondelete="RESTRICT"),
        sa.CheckConstraint("avg_occupancy >= 0", name="ck_buckets_avg"),
        sa.CheckConstraint("min_occupancy >= 0", name="ck_buckets_min"),
        sa.CheckConstraint("max_occupancy >= min_occupancy", name="ck_buckets_max"),
        sa.CheckConstraint("min_occupancy <= avg_occupancy AND avg_occupancy <= max_occupancy", name="ck_buckets_order"),
        sa.CheckConstraint("capacity_snapshot > 0", name="ck_buckets_capacity"),
        sa.CheckConstraint("coverage_percentage BETWEEN 0 AND 100", name="ck_buckets_coverage"),
        sa.CheckConstraint("sample_count >= 0 AND sample_count <= expected_sample_count", name="ck_buckets_counts"),
        sa.CheckConstraint("expected_sample_count > 0", name="ck_buckets_expected"),
    )
    op.create_index("ix_occupancy_buckets_time", "occupancy_buckets_5m", ["bucket_start"])


def downgrade() -> None:
    op.drop_index("ix_occupancy_buckets_time", table_name="occupancy_buckets_5m")
    op.drop_table("occupancy_buckets_5m")
    op.drop_index("ix_occupancy_samples_observed_at", table_name="occupancy_samples")
    op.drop_index("ix_occupancy_samples_camera_time", table_name="occupancy_samples")
    op.drop_table("occupancy_samples")
    op.drop_table("camera_states")
    op.drop_table("cameras")
    op.drop_table("rooms")
