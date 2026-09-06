from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator
from uuid import UUID


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


class AssistantQueryRequest(ApiModel):
    message: str = Field(min_length=1, max_length=1_000)
    conversation_id: UUID | None = None

    @field_validator("message", mode="before")
    @classmethod
    def normalize_message(cls, value):
        return value.strip() if isinstance(value, str) else value


class AssistantResult(ApiModel):
    room_id: str = Field(pattern=r"^room_[a-z0-9_]+$")
    name: str
    building: str
    floor: int = Field(ge=0)
    block: str
    capacity: int = Field(gt=0)
    occupancy: int = Field(ge=0)
    occupancy_percentage: float = Field(ge=0, le=100)
    available_capacity: int = Field(ge=0)
    status: CameraStatus
    observed_at: UtcDateTime
    reason: str


class AssistantAppliedFilters(ApiModel):
    buildings: list[str] = Field(default_factory=list)
    floors: list[int] = Field(default_factory=list)
    blocks: list[str] = Field(default_factory=list)
    maximum_occupancy_percentage: float | None = Field(default=None, ge=0, le=100)
    minimum_available_capacity: int | None = Field(default=None, ge=0)
    limit: int = Field(default=3, ge=1, le=10)


class AssistantQueryResponse(ApiModel):
    conversation_id: UUID
    answer: str
    results: list[AssistantResult]
    applied_filters: AssistantAppliedFilters
    data_timestamp: UtcDateTime
    warnings: list[str]


class AssistantConversationSummary(ApiModel):
    id: UUID
    title: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
    message_count: int = Field(ge=0)


class AssistantConversationListResponse(ApiModel):
    items: list[AssistantConversationSummary]
    page: int = Field(ge=1)
    limit: int = Field(ge=1, le=50)
    next_page: int | None = Field(default=None, ge=2)


class AssistantMessage(ApiModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    structured_results: dict[str, Any] | None = None
    created_at: UtcDateTime


class AssistantConversation(ApiModel):
    id: UUID
    title: str | None
    created_at: UtcDateTime
    updated_at: UtcDateTime
    messages: list[AssistantMessage]


class SignupRequest(ApiModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class LoginRequest(ApiModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class PublicUser(ApiModel):
    id: str
    name: str
    email: str
    role: str
    created_at: UtcDateTime


class AuthResponse(ApiModel):
    data: PublicUser


class Profile(ApiModel):
    id: str
    name: str
    email: str
    created_at: UtcDateTime
    updated_at: UtcDateTime


class ProfileUpdateRequest(ApiModel):
    name: str


class ChangePasswordRequest(ApiModel):
    current_password: str
    new_password: str


class Notification(ApiModel):
    id: str
    type: str
    category: str
    title: str
    message: str
    room_id: str | None = None
    suggested_room_id: str | None = None
    occupancy_percentage: float | None = Field(default=None, ge=0, le=100)
    created_at: UtcDateTime
    read_at: UtcDateTime | None = None
    dismissed_at: UtcDateTime | None = None


class NotificationsResponse(ApiModel):
    items: list[Notification]
    unread_count: int = Field(ge=0)
    next_cursor: str | None = None


class NotificationPreferences(ApiModel):
    in_app_enabled: bool
    high_occupancy_enabled: bool
    high_occupancy_threshold: int = Field(ge=50, le=100)
    cooldown_minutes: int = Field(gt=0, le=10_080)
    favorite_floors: list[int] = Field(default_factory=list, max_length=8)

    @field_validator("favorite_floors", mode="before")
    @classmethod
    def validate_favorite_floors(cls, value):
        if not isinstance(value, list) or any(
               isinstance(floor, bool) or not isinstance(floor, int) or floor < 2 or floor > 9
               for floor in value):
            raise ValueError("Favorite floors must be whole numbers from 2 through 9")
        if len(set(value)) != len(value):
            raise ValueError("Favorite floors must not contain duplicates")
        return sorted(value)


class NotificationPreferencesUpdate(ApiModel):
    in_app_enabled: bool | None = Field(default=None, strict=True)
    high_occupancy_enabled: bool | None = Field(default=None, strict=True)
    high_occupancy_threshold: int | None = Field(default=None, strict=True, ge=50, le=100)
    cooldown_minutes: int | None = Field(default=None, strict=True, gt=0, le=10_080)
    favorite_floors: list[int] | None = Field(default=None, max_length=8)

    @field_validator("favorite_floors", mode="before")
    @classmethod
    def validate_favorite_floors(cls, value):
        if value is None:
            return value
        if not isinstance(value, list) or any(
               isinstance(floor, bool) or not isinstance(floor, int) or floor < 2 or floor > 9
               for floor in value):
            raise ValueError("Favorite floors must be whole numbers from 2 through 9")
        if len(set(value)) != len(value):
            raise ValueError("Favorite floors must not contain duplicates")
        return sorted(value)

    @model_validator(mode="after")
    def require_non_null_update(self):
        provided = self.model_fields_set
        if not provided or any(getattr(self, field) is None for field in provided):
            raise ValueError("At least one non-null preference is required")
        return self
