from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    data_source: str = "mock"
    mock_data_dir: Path = PROJECT_ROOT / "mock" / "generated"
    frontend_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @classmethod
    def from_env(cls) -> "Settings":
        data_source = os.getenv("DATA_SOURCE", "mock").strip().lower()
        configured_dir = os.getenv("MOCK_DATA_DIR")
        mock_data_dir = Path(configured_dir).expanduser() if configured_dir else PROJECT_ROOT / "mock" / "generated"
        origins = tuple(
            origin.strip()
            for origin in os.getenv(
                "FRONTEND_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        )
        return cls(data_source=data_source, mock_data_dir=mock_data_dir.resolve(), frontend_origins=origins)

