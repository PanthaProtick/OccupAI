from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
    create_engine, event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class RoomRow(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_rooms_name"),
        CheckConstraint("capacity > 0", name="ck_rooms_capacity"),
        CheckConstraint("length(trim(building)) > 0", name="ck_rooms_building"),
        CheckConstraint("floor >= 0", name="ck_rooms_floor"),
        CheckConstraint("length(trim(behavior_profile)) > 0", name="ck_rooms_profile"),
    )
    room_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    capacity: Mapped[int] = mapped_column(Integer)
    building: Mapped[str] = mapped_column(String)
    floor: Mapped[int] = mapped_column(Integer)
    behavior_profile: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
    camera: Mapped["CameraRow"] = relationship(back_populates="room", uselist=False)


class CameraRow(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        CheckConstraint("enabled IN (0, 1)", name="ck_cameras_enabled"),
        CheckConstraint("stale_after_seconds > 0", name="ck_cameras_stale_after"),
    )
    camera_id: Mapped[str] = mapped_column(String, primary_key=True)
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.room_id", onupdate="CASCADE", ondelete="RESTRICT"), unique=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    stale_after_seconds: Mapped[float] = mapped_column(Float, default=10)
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
    room: Mapped[RoomRow] = relationship(back_populates="camera")
    state: Mapped["CameraStateRow | None"] = relationship(back_populates="camera", uselist=False)


class CameraStateRow(Base):
    __tablename__ = "camera_states"
    __table_args__ = (
        CheckConstraint("raw_occupancy IS NULL OR raw_occupancy >= 0", name="ck_states_raw"),
        CheckConstraint("occupancy IS NULL OR occupancy >= 0", name="ck_states_occupancy"),
        CheckConstraint("status IN ('online','stale','offline')", name="ck_states_status"),
    )
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.camera_id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    raw_occupancy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occupancy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String)
    observed_at: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_at: Mapped[str] = mapped_column(String)
    diagnostics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera: Mapped[CameraRow] = relationship(back_populates="state")


class OccupancySampleRow(Base):
    __tablename__ = "occupancy_samples"
    __table_args__ = (
        CheckConstraint("raw_occupancy >= 0", name="ck_samples_raw"),
        CheckConstraint("occupancy >= 0", name="ck_samples_occupancy"),
        CheckConstraint("status IN ('online','stale')", name="ck_samples_status"),
        CheckConstraint("capacity_snapshot > 0", name="ck_samples_capacity"),
        UniqueConstraint("camera_id", "observed_at", name="uq_samples_camera_observed"),
        UniqueConstraint("camera_id", "source_event_id", name="uq_samples_camera_event"),
        Index("ix_occupancy_samples_camera_time", "camera_id", "observed_at"),
        Index("ix_occupancy_samples_observed_at", "observed_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.camera_id", onupdate="CASCADE", ondelete="RESTRICT"))
    observed_at: Mapped[str] = mapped_column(String)
    raw_occupancy: Mapped[int] = mapped_column(Integer)
    occupancy: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String)
    capacity_snapshot: Mapped[int] = mapped_column(Integer)
    source_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[str] = mapped_column(String)


class IngestionReceiptRow(Base):
    __tablename__ = "ingestion_receipts"
    __table_args__ = (
        UniqueConstraint("camera_id", "observed_at", name="uq_receipts_camera_observed"),
        UniqueConstraint("camera_id", "source_event_id", name="uq_receipts_camera_event"),
        Index("ix_ingestion_receipts_observed_at", "observed_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    camera_id: Mapped[str] = mapped_column(
        ForeignKey("cameras.camera_id", onupdate="CASCADE", ondelete="CASCADE")
    )
    observed_at: Mapped[str] = mapped_column(String)
    source_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    accepted_at: Mapped[str] = mapped_column(String)


class OccupancyBucketRow(Base):
    __tablename__ = "occupancy_buckets_5m"
    __table_args__ = (
        CheckConstraint("avg_occupancy >= 0", name="ck_buckets_avg"),
        CheckConstraint("min_occupancy >= 0", name="ck_buckets_min"),
        CheckConstraint("max_occupancy >= min_occupancy", name="ck_buckets_max"),
        CheckConstraint("min_occupancy <= avg_occupancy AND avg_occupancy <= max_occupancy", name="ck_buckets_order"),
        CheckConstraint("capacity_snapshot > 0", name="ck_buckets_capacity"),
        CheckConstraint("coverage_percentage BETWEEN 0 AND 100", name="ck_buckets_coverage"),
        CheckConstraint("sample_count >= 0 AND sample_count <= expected_sample_count", name="ck_buckets_counts"),
        CheckConstraint("expected_sample_count > 0", name="ck_buckets_expected"),
        Index("ix_occupancy_buckets_time", "bucket_start"),
    )
    camera_id: Mapped[str] = mapped_column(ForeignKey("cameras.camera_id", onupdate="CASCADE", ondelete="RESTRICT"), primary_key=True)
    bucket_start: Mapped[str] = mapped_column(String, primary_key=True)
    avg_occupancy: Mapped[float] = mapped_column(Float)
    min_occupancy: Mapped[int] = mapped_column(Integer)
    max_occupancy: Mapped[int] = mapped_column(Integer)
    capacity_snapshot: Mapped[int] = mapped_column(Integer)
    coverage_percentage: Mapped[float] = mapped_column(Float)
    sample_count: Mapped[int] = mapped_column(Integer)
    expected_sample_count: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[str] = mapped_column(String)


def create_database_engine(url: str, busy_timeout_ms: int = 5000):
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def configure_sqlite(dbapi_connection, _):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")
            cursor.close()
    return engine


def make_session_factory(engine):
    return sessionmaker(engine, expire_on_commit=False)
