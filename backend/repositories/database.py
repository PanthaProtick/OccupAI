from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from backend.database import CameraRow, CameraStateRow, OccupancyBucketRow, RoomRow
from backend.models import CameraStatus, HistoryMetric, HistoryPoint, HistoryRange, Occupancy, Room, RoomView


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError(f"Database timestamp is not UTC: {value}")
    return parsed.astimezone(timezone.utc)


def _intensity(percentage: float | None) -> str | None:
    if percentage is None:
        return None
    return "Low" if percentage < 25 else "Moderate" if percentage < 50 else "Busy" if percentage < 80 else "Very Busy"


class DatabaseOccupancyRepository:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    @property
    def generated_at(self) -> datetime:
        with self.session_factory() as session:
            value = session.scalar(select(CameraStateRow.updated_at).order_by(CameraStateRow.updated_at.desc()).limit(1))
        return _dt(value) if value else datetime.now(timezone.utc)

    @property
    def history_generated_at(self) -> datetime | None:
        with self.session_factory() as session:
            value = session.scalar(select(OccupancyBucketRow.updated_at).order_by(OccupancyBucketRow.updated_at.desc()).limit(1))
        return _dt(value) if value else None

    @staticmethod
    def _room(row: RoomRow, camera: CameraRow) -> Room:
        return Room(room_id=row.room_id, name=row.name, capacity=row.capacity, building=row.building,
                    floor=row.floor, camera_id=camera.camera_id, behavior_profile=row.behavior_profile)

    @staticmethod
    def _occupancy(room: RoomRow, camera: CameraRow, state: CameraStateRow | None) -> Occupancy:
        updated = _dt(state.updated_at) if state else _dt(camera.updated_at)
        status = CameraStatus(state.status) if state else CameraStatus.OFFLINE
        if state and status is CameraStatus.ONLINE and state.observed_at:
            age = datetime.now(timezone.utc) - _dt(state.observed_at)
            if age.total_seconds() > camera.stale_after_seconds:
                status = CameraStatus.STALE
        value = state.occupancy if state and status is not CameraStatus.OFFLINE else None
        percentage = round(min(value / room.capacity * 100, 100), 2) if value is not None else None
        return Occupancy(camera_id=camera.camera_id, room_id=room.room_id, occupancy=value,
                         raw_occupancy=state.raw_occupancy if state else None, capacity=room.capacity,
                         occupancy_percentage=percentage, status=status, updated_at=updated)

    def list_rooms(self) -> list[Room]:
        with self.session_factory() as session:
            rows = session.execute(select(RoomRow, CameraRow).join(CameraRow).order_by(CameraRow.camera_id)).all()
            return [self._room(room, camera) for room, camera in rows]

    def get_room(self, room_id: str) -> RoomView | None:
        with self.session_factory() as session:
            row = session.execute(select(RoomRow, CameraRow, CameraStateRow).select_from(RoomRow).join(CameraRow, CameraRow.room_id == RoomRow.room_id).outerjoin(CameraStateRow, CameraStateRow.camera_id == CameraRow.camera_id).where(RoomRow.room_id == room_id)).first()
            if not row:
                return None
            room, camera, state = row
            base, occupancy = self._room(room, camera), self._occupancy(room, camera, state)
            return RoomView(**base.model_dump(), occupancy=occupancy.occupancy, raw_occupancy=occupancy.raw_occupancy,
                            occupancy_percentage=occupancy.occupancy_percentage, intensity=_intensity(occupancy.occupancy_percentage),
                            status=occupancy.status, updated_at=occupancy.updated_at)

    def list_occupancy(self) -> list[Occupancy]:
        with self.session_factory() as session:
            rows = session.execute(select(RoomRow, CameraRow, CameraStateRow).select_from(RoomRow).join(CameraRow, CameraRow.room_id == RoomRow.room_id).outerjoin(CameraStateRow, CameraStateRow.camera_id == CameraRow.camera_id).order_by(CameraRow.camera_id)).all()
            return [self._occupancy(*row) for row in rows]

    def get_occupancy(self, camera_id: str) -> Occupancy | None:
        with self.session_factory() as session:
            row = session.execute(select(RoomRow, CameraRow, CameraStateRow).select_from(RoomRow).join(CameraRow, CameraRow.room_id == RoomRow.room_id).outerjoin(CameraStateRow, CameraStateRow.camera_id == CameraRow.camera_id).where(CameraRow.camera_id == camera_id)).first()
            return self._occupancy(*row) if row else None

    def get_history(self, room_id: str, history_range: HistoryRange, metric: HistoryMetric) -> list[HistoryPoint] | None:
        with self.session_factory() as session:
            camera = session.scalar(select(CameraRow).where(CameraRow.room_id == room_id))
            if camera is None:
                return None
            latest = session.scalar(select(OccupancyBucketRow.bucket_start).where(
                OccupancyBucketRow.camera_id == camera.camera_id
            ).order_by(OccupancyBucketRow.bucket_start.desc()).limit(1))
            if latest is None:
                return []
            cutoff = _dt(latest) - timedelta(days=7)
            cutoff_text = cutoff.isoformat().replace("+00:00", "Z")
            buckets = session.scalars(select(OccupancyBucketRow).where(
                OccupancyBucketRow.camera_id == camera.camera_id,
                OccupancyBucketRow.bucket_start > cutoff_text,
            ).order_by(OccupancyBucketRow.bucket_start)).all()
        grouping = {HistoryRange.HOUR: 12, HistoryRange.DAY: 288, HistoryRange.WEEK: 2016}[history_range]
        grouped: dict[datetime, list[OccupancyBucketRow]] = {}
        first = _dt(buckets[0].bucket_start) if buckets else None
        for bucket in buckets:
            stamp = _dt(bucket.bucket_start)
            if history_range is HistoryRange.HOUR:
                key = stamp.replace(minute=0, second=0, microsecond=0)
            elif history_range is HistoryRange.DAY:
                key = stamp.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                key = first.replace(hour=0, minute=0, second=0, microsecond=0)  # retained dataset bucket
            grouped.setdefault(key, []).append(bucket)
        points: list[HistoryPoint] = []
        for key, chunk in sorted(grouped.items()):
            samples = sum(item.sample_count for item in chunk)
            if samples == 0:
                continue
            weighted = sum(item.avg_occupancy * item.sample_count for item in chunk) / samples
            expected = grouping * max(item.expected_sample_count for item in chunk)
            if metric is HistoryMetric.OCCUPANCY:
                value = weighted
            else:
                value = sum(
                    min(item.avg_occupancy / item.capacity_snapshot * 100, 100) * item.sample_count
                    for item in chunk
                ) / samples
            points.append(HistoryPoint(bucket_start=key, value=round(value, 2),
                                       coverage_percentage=round(samples / expected * 100, 2)))
        return points

    def close(self) -> None:
        return None
