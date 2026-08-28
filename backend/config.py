from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_URL = "sqlite:///./data/occupai.db"


@dataclass(frozen=True)
class Settings:
    data_source: str = "mock"
    mock_data_dir: Path = PROJECT_ROOT / "mock" / "generated"
    frontend_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    database_url: str = DEFAULT_DATABASE_URL
    sqlite_busy_timeout_ms: int = 5000
    raw_sample_interval_seconds: float = 10.0
    raw_sample_retention_days: int = 30
    aggregate_retention_days: int = 365
    retention_batch_size: int = 1000
    ingestion_enabled: bool = False
    model_server_url: str = "http://127.0.0.1:8001"
    model_server_timeout_seconds: float = 2.0
    model_server_poll_interval_seconds: float = 2.0
    live_camera_ids: tuple[str, ...] = ("cam_001", "cam_002", "cam_003")
    maintenance_enabled: bool = False
    maintenance_interval_seconds: float = 60.0
    simulation_enabled: bool = False
    simulation_tick_interval_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.data_source not in {"mock", "database"}:
            raise ValueError("DATA_SOURCE must be 'mock' or 'database'")
        positive = {
            "SQLITE_BUSY_TIMEOUT_MS": self.sqlite_busy_timeout_ms,
            "RAW_SAMPLE_INTERVAL_SECONDS": self.raw_sample_interval_seconds,
            "RAW_SAMPLE_RETENTION_DAYS": self.raw_sample_retention_days,
            "AGGREGATE_RETENTION_DAYS": self.aggregate_retention_days,
            "RETENTION_BATCH_SIZE": self.retention_batch_size,
            "MODEL_SERVER_TIMEOUT_SECONDS": self.model_server_timeout_seconds,
            "MODEL_SERVER_POLL_INTERVAL_SECONDS": self.model_server_poll_interval_seconds,
            "MAINTENANCE_INTERVAL_SECONDS": self.maintenance_interval_seconds,
            "SIMULATION_TICK_INTERVAL_SECONDS": self.simulation_tick_interval_seconds,
        }
        invalid = [name for name, value in positive.items() if value <= 0]
        if invalid:
            raise ValueError(f"Configuration values must be positive: {', '.join(invalid)}")
        if not self.database_url.strip():
            raise ValueError("DATABASE_URL must not be empty")
        if self.raw_sample_interval_seconds < 5 or self.raw_sample_interval_seconds > 10:
            raise ValueError("RAW_SAMPLE_INTERVAL_SECONDS must be between 5 and 10")
        if self.ingestion_enabled and self.data_source != "database":
            raise ValueError("INGESTION_ENABLED requires DATA_SOURCE=database")
        if self.maintenance_enabled and self.data_source != "database":
            raise ValueError("MAINTENANCE_ENABLED requires DATA_SOURCE=database")
        if self.simulation_enabled and self.data_source != "database":
            raise ValueError("SIMULATION_ENABLED requires DATA_SOURCE=database")
        if len(set(self.live_camera_ids)) != len(self.live_camera_ids) or any(
            re.fullmatch(r"cam_\d{3}", camera_id) is None for camera_id in self.live_camera_ids
        ):
            raise ValueError("LIVE_CAMERA_IDS must contain unique canonical cam_NNN identifiers")

    def safe_summary(self) -> dict[str, object]:
        return {
            "data_source": self.data_source,
            "frontend_origin_count": len(self.frontend_origins),
            "sqlite_busy_timeout_ms": self.sqlite_busy_timeout_ms,
            "raw_sample_interval_seconds": self.raw_sample_interval_seconds,
            "raw_sample_retention_days": self.raw_sample_retention_days,
            "aggregate_retention_days": self.aggregate_retention_days,
            "retention_batch_size": self.retention_batch_size,
            "ingestion_enabled": self.ingestion_enabled,
            "live_camera_count": len(self.live_camera_ids),
            "maintenance_enabled": self.maintenance_enabled,
            "simulation_enabled": self.simulation_enabled,
        }

    @classmethod
    def from_env(cls) -> "Settings":
        # Read the repository's local configuration for direct ``uvicorn``
        # launches, without writing values into ``os.environ``.  Process
        # variables deliberately win for deployment and test isolation.
        file_values = dotenv_values(PROJECT_ROOT / "backend" / ".env")

        def setting(name: str, default: str) -> str:
            return os.getenv(name, file_values.get(name) or default)

        data_source = setting("DATA_SOURCE", "mock").strip().lower()
        configured_dir = setting("MOCK_DATA_DIR", "")
        mock_data_dir = Path(configured_dir).expanduser() if configured_dir else PROJECT_ROOT / "mock" / "generated"
        origins = tuple(
            origin.strip()
            for origin in setting(
                "FRONTEND_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
        return cls(
            data_source=data_source,
            mock_data_dir=mock_data_dir.resolve(),
            frontend_origins=origins,
            database_url=setting("DATABASE_URL", DEFAULT_DATABASE_URL),
            sqlite_busy_timeout_ms=int(setting("SQLITE_BUSY_TIMEOUT_MS", "5000")),
            raw_sample_interval_seconds=float(setting("RAW_SAMPLE_INTERVAL_SECONDS", "10")),
            raw_sample_retention_days=int(setting("RAW_SAMPLE_RETENTION_DAYS", "30")),
            aggregate_retention_days=int(setting("AGGREGATE_RETENTION_DAYS", "365")),
            retention_batch_size=int(setting("RETENTION_BATCH_SIZE", "1000")),
            ingestion_enabled=setting("INGESTION_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
            model_server_url=setting("MODEL_SERVER_URL", "http://127.0.0.1:8001"),
            model_server_timeout_seconds=float(setting("MODEL_SERVER_TIMEOUT_SECONDS", "2")),
            model_server_poll_interval_seconds=float(setting("MODEL_SERVER_POLL_INTERVAL_SECONDS", "2")),
            live_camera_ids=tuple(value.strip() for value in setting(
                "LIVE_CAMERA_IDS", "cam_001,cam_002,cam_003"
            ).split(",") if value.strip()),
            maintenance_enabled=setting("MAINTENANCE_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
            maintenance_interval_seconds=float(setting("MAINTENANCE_INTERVAL_SECONDS", "60")),
            simulation_enabled=setting("SIMULATION_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
            simulation_tick_interval_seconds=float(setting("SIMULATION_TICK_INTERVAL_SECONDS", "10")),
        )

