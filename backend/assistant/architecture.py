from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

from backend.models import CameraStatus, Occupancy, Room


# This allowlist is the maximum factual room/state surface that later assistant
# response models may expose. Provider credentials, database details, internal
# authorization data, and raw unrestricted records are intentionally absent.
BROWSER_SAFE_RESULT_FIELDS = frozenset({
    "room_id",
    "name",
    "building",
    "floor",
    "block",
    "capacity",
    "occupancy",
    "occupancy_percentage",
    "available_capacity",
    "status",
    "observed_at",
    "reason",
})

FORBIDDEN_BROWSER_FIELDS = frozenset({
    "database_url",
    "password",
    "password_hash",
    "session_token",
    "token_hash",
    "authorization",
    "auth_session_pepper",
    "assistant_api_key",
    "provider_api_key",
    "system_prompt",
})


@runtime_checkable
class AssistantOccupancySource(Protocol):
    """Read-only backend data boundary used by future assistant services.

    Implementations return validated public domain models.  The browser and an
    optional language-model provider never receive this source or a DB session.
    """

    @property
    def generated_at(self) -> datetime: ...

    def list_rooms(self) -> list[Room]: ...

    def list_occupancy(self) -> list[Occupancy]: ...

    def list_assistant_snapshots(self) -> list["AssistantRoomSnapshot"]: ...


@dataclass(frozen=True)
class AssistantRoomSnapshot:
    """Backend-only joined room/feed state used for trust validation."""

    room: Room
    occupancy: Occupancy
    camera_enabled: bool
    observed_at: datetime | None
    is_fresh: bool

    @property
    def status(self) -> CameraStatus:
        return self.occupancy.status


@dataclass(frozen=True)
class AssistantArchitecture:
    execution_tier: str = "backend"
    browser_transport: str = "occupai_api_only"
    data_access: str = "validated_repository"
    provider_database_access: bool = False
    provider_arbitrary_tool_access: bool = False
    factual_ranking_owner: str = "deterministic_backend"

    def __post_init__(self) -> None:
        if self.execution_tier != "backend" or self.browser_transport != "occupai_api_only":
            raise ValueError("The Campus Assistant must remain behind the OccupAI backend")
        if self.provider_database_access or self.provider_arbitrary_tool_access:
            raise ValueError("Assistant providers cannot access databases or arbitrary tools")
        if BROWSER_SAFE_RESULT_FIELDS & FORBIDDEN_BROWSER_FIELDS:
            raise ValueError("Browser-safe assistant fields cannot contain sensitive fields")


ASSISTANT_ARCHITECTURE = AssistantArchitecture()
