from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _require_utc(value: datetime) -> datetime:
    if value.utcoffset() != timedelta(0):
        raise ValueError("timestamp must include a UTC offset")
    return value


UtcDateTime = Annotated[datetime, AfterValidator(_require_utc)]


class CameraStatus(StrEnum):
    ONLINE = "online"
    STALE = "stale"
    OFFLINE = "offline"


class HistoryRange(StrEnum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


class HistoryMetric(StrEnum):
    OCCUPANCY = "occupancy"
    PERCENTAGE = "percentage"


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Room(ApiModel):
    room_id: str = Field(pattern=r"^room_[a-z0-9_]+$")
    name: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    building: str = Field(min_length=1)
    floor: int = Field(ge=0)
    camera_id: str = Field(pattern=r"^cam_\d{3}$")
    behavior_profile: str = Field(min_length=1)


class Occupancy(ApiModel):
    camera_id: str = Field(pattern=r"^cam_\d{3}$")
    room_id: str = Field(pattern=r"^room_[a-z0-9_]+$")
    occupancy: int | None = Field(default=None, ge=0)
    raw_occupancy: int | None = Field(default=None, ge=0)
    capacity: int = Field(gt=0)
    occupancy_percentage: float | None = Field(default=None, ge=0, le=100)
    status: CameraStatus
    updated_at: UtcDateTime


class RoomView(Room):
    occupancy: int | None = Field(default=None, ge=0)
    raw_occupancy: int | None = Field(default=None, ge=0)
    occupancy_percentage: float | None = Field(default=None, ge=0, le=100)
    intensity: str | None = None
    status: CameraStatus
    updated_at: UtcDateTime


class HistoryPoint(ApiModel):
    bucket_start: UtcDateTime
    value: float = Field(ge=0)
    coverage_percentage: float = Field(default=100.0, ge=0, le=100)


class CollectionMeta(ApiModel):
    count: int = Field(ge=0)
    generated_at: UtcDateTime | None = None


class RoomsResponse(ApiModel):
    data: list[Room]
    meta: CollectionMeta


class RoomResponse(ApiModel):
    data: RoomView


class OccupancyListResponse(ApiModel):
    data: list[Occupancy]
    meta: CollectionMeta


class OccupancyResponse(ApiModel):
    data: Occupancy


class HistoryMeta(ApiModel):
    room_id: str
    range: HistoryRange
    metric: HistoryMetric
    count: int = Field(ge=0)
    generated_at: UtcDateTime | None = None


class HistoryResponse(ApiModel):
    data: list[HistoryPoint]
    meta: HistoryMeta


class HealthResponse(ApiModel):
    status: str = "ok"
    data_source: str


class ErrorBody(ApiModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(ApiModel):
    error: ErrorBody
