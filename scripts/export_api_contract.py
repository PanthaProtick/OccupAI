"""Regenerate the checked-in OpenAPI contract and compact API examples."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = PROJECT_ROOT / "contracts"
EXAMPLE_DIR = CONTRACT_DIR / "examples"
app = create_app(Settings())


def write_json(filename: str, payload: object) -> None:
    (EXAMPLE_DIR / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    CONTRACT_DIR.mkdir(exist_ok=True)
    EXAMPLE_DIR.mkdir(exist_ok=True)
    contract = app.openapi()
    (CONTRACT_DIR / "openapi.yaml").write_text(
        yaml.safe_dump(contract, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        requests = {
            "health.json": ("/health", {}),
            "rooms.json": ("/api/rooms", {}),
            "occupancy.json": ("/api/occupancy", {}),
            "stale-room.json": ("/api/rooms/room_canteen", {}),
            "offline-camera.json": ("/api/occupancy/cam_005", {}),
            "history.json": (
                "/api/history",
                {"params": {"room_id": "room_tt_ground", "range": "week", "metric": "percentage"}},
            ),
            "not-found-error.json": ("/api/occupancy/cam_999", {}),
            "validation-error.json": (
                "/api/history",
                {"params": {"room_id": "room_tt_ground", "range": "month", "metric": "percentage"}},
            ),
        }
        for filename, (path, kwargs) in requests.items():
            response = client.get(path, **kwargs)
            write_json(filename, response.json())

    write_json(
        "zero-occupancy.json",
        {
            "data": {
                "camera_id": "cam_005",
                "room_id": "room_study_room",
                "occupancy": 0,
                "raw_occupancy": 0,
                "capacity": 80,
                "occupancy_percentage": 0.0,
                "status": "online",
                "updated_at": "2026-08-19T13:00:00Z",
            }
        },
    )
    write_json(
        "over-capacity.json",
        {
            "data": {
                "camera_id": "cam_003",
                "room_id": "room_canteen",
                "occupancy": 126,
                "raw_occupancy": 126,
                "capacity": 120,
                "occupancy_percentage": 100.0,
                "status": "online",
                "updated_at": "2026-08-19T13:00:00Z",
            }
        },
    )
    write_json(
        "empty-history.json",
        {
            "data": [],
            "meta": {
                "room_id": "room_1a03",
                "range": "hour",
                "metric": "occupancy",
                "count": 0,
                "generated_at": "2026-08-19T13:00:00Z",
            },
        },
    )
    write_json(
        "partial-coverage-history.json",
        {
            "data": [
                {
                    "bucket_start": "2026-08-15T09:00:00Z",
                    "value": 18.0,
                    "coverage_percentage": 62.5,
                }
            ],
            "meta": {
                "room_id": "room_1a04",
                "range": "hour",
                "metric": "occupancy",
                "count": 1,
                "generated_at": "2026-08-19T13:00:00Z",
            },
        },
    )

    print(f"Exported API contract and {len(requests) + 4} examples to {CONTRACT_DIR}")


if __name__ == "__main__":
    main()
