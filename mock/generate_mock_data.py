"""Generate deterministic, scenario-based OccupAI mock data.

The generator has no external dependencies and is intentionally file-oriented so
model-server, backend, and frontend work can consume the same fixtures directly.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SEED = 42
BUCKET_MINUTES = 5
HISTORY_DAYS = 7
DEFAULT_START = datetime(2026, 8, 12, 0, 0, tzinfo=timezone.utc)


ROOMS: list[dict[str, Any]] = [
    {"room_id": "room_cse_201", "name": "CSE 201", "capacity": 40, "building": "CSE Building", "floor": 2, "camera_id": "cam_001", "behavior_profile": "classroom"},
    {"room_id": "room_cse_202", "name": "CSE 202", "capacity": 35, "building": "CSE Building", "floor": 2, "camera_id": "cam_002", "behavior_profile": "classroom"},
    {"room_id": "room_library_01", "name": "Library Reading Room", "capacity": 80, "building": "Central Library", "floor": 1, "camera_id": "cam_003", "behavior_profile": "library"},
    {"room_id": "room_library_02", "name": "Library Study Room", "capacity": 12, "building": "Central Library", "floor": 3, "camera_id": "cam_004", "behavior_profile": "study_room"},
    {"room_id": "room_canteen", "name": "Main Canteen", "capacity": 120, "building": "Student Center", "floor": 1, "camera_id": "cam_005", "behavior_profile": "canteen"},
    {"room_id": "room_ece_105", "name": "ECE 105 Lab", "capacity": 50, "building": "ECE Building", "floor": 1, "camera_id": "cam_006", "behavior_profile": "classroom"},
    {"room_id": "room_common_01", "name": "Student Common Room", "capacity": 60, "building": "Student Center", "floor": 2, "camera_id": "cam_007", "behavior_profile": "study_room"},
    {"room_id": "room_cse_301", "name": "CSE 301", "capacity": 45, "building": "CSE Building", "floor": 3, "camera_id": "cam_008", "behavior_profile": "classroom"},
    {"room_id": "room_cse_302", "name": "CSE 302", "capacity": 30, "building": "CSE Building", "floor": 3, "camera_id": "cam_009", "behavior_profile": "classroom"},
    {"room_id": "room_eee_101", "name": "EEE 101 Lab", "capacity": 55, "building": "EEE Building", "floor": 1, "camera_id": "cam_010", "behavior_profile": "classroom"},
    {"room_id": "room_eee_201", "name": "EEE 201", "capacity": 40, "building": "EEE Building", "floor": 2, "camera_id": "cam_011", "behavior_profile": "classroom"},
    {"room_id": "room_library_03", "name": "Library Computer Lab", "capacity": 30, "building": "Central Library", "floor": 2, "camera_id": "cam_012", "behavior_profile": "library"},
    {"room_id": "room_auditorium", "name": "Main Auditorium", "capacity": 200, "building": "Admin Building", "floor": 1, "camera_id": "cam_013", "behavior_profile": "classroom"},
    {"room_id": "room_seminar_01", "name": "Seminar Room A", "capacity": 25, "building": "Admin Building", "floor": 2, "camera_id": "cam_014", "behavior_profile": "classroom"},
    {"room_id": "room_seminar_02", "name": "Seminar Room B", "capacity": 25, "building": "Admin Building", "floor": 2, "camera_id": "cam_015", "behavior_profile": "classroom"},
    {"room_id": "room_canteen_02", "name": "Faculty Cafeteria", "capacity": 60, "building": "Faculty Building", "floor": 1, "camera_id": "cam_016", "behavior_profile": "canteen"},
    {"room_id": "room_gym", "name": "Gymnasium", "capacity": 100, "building": "Sports Complex", "floor": 1, "camera_id": "cam_017", "behavior_profile": "study_room"},
    {"room_id": "room_workshop", "name": "Workshop Hall", "capacity": 70, "building": "ECE Building", "floor": 0, "camera_id": "cam_018", "behavior_profile": "classroom"},
    {"room_id": "room_common_02", "name": "Graduate Lounge", "capacity": 20, "building": "Faculty Building", "floor": 3, "camera_id": "cam_019", "behavior_profile": "study_room"},
    {"room_id": "room_prayer", "name": "Prayer Room", "capacity": 50, "building": "Student Center", "floor": 1, "camera_id": "cam_020", "behavior_profile": "study_room"},
]


def iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def gaussian_peak(hour: float, center: float, width: float) -> float:
    return math.exp(-((hour - center) ** 2) / (2 * width**2))


def weekday_factor(day: int) -> float:
    return 0.30 if day >= 5 else 1.0


def expected_occupancy(profile: str, hour: float, day: int) -> float:
    """Return a smooth occupancy fraction before controlled random variation."""
    day_factor = weekday_factor(day)
    if profile == "classroom":
        # Sharp class-time peaks, with a lunch dip and near-empty nights.
        value = 0.04 + 0.78 * gaussian_peak(hour, 10.0, 1.15) + 0.62 * gaussian_peak(hour, 14.5, 1.25)
        return clamp(value * day_factor, 0.0, 0.95)
    if profile == "library":
        # Gradual opening/ramp-up and sustained daytime occupancy.
        opening = clamp((hour - 7.0) / 2.5, 0.0, 1.0)
        closing = clamp((19.0 - hour) / 3.0, 0.0, 1.0)
        return clamp((0.10 + 0.52 * opening * closing) * day_factor, 0.0, 0.85)
    if profile == "study_room":
        return clamp((0.05 + 0.42 * gaussian_peak(hour, 16.0, 4.0) + 0.18 * gaussian_peak(hour, 21.0, 2.0)) * day_factor, 0.0, 0.75)
    if profile == "canteen":
        value = 0.04 + 0.35 * gaussian_peak(hour, 8.0, 1.0) + 0.92 * gaussian_peak(hour, 13.0, 1.35) + 0.42 * gaussian_peak(hour, 19.0, 1.7)
        return clamp(value * day_factor, 0.0, 0.98)
    raise ValueError(f"Unknown behavior profile: {profile}")


def intensity(percentage: float) -> str:
    if percentage < 25:
        return "Low"
    if percentage < 50:
        return "Moderate"
    if percentage < 80:
        return "Busy"
    return "Very Busy"


def generate_history(rng: random.Random, start: datetime) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    buckets = HISTORY_DAYS * 24 * 60 // BUCKET_MINUTES
    for room in ROOMS:
        for index in range(buckets):
            timestamp = start + timedelta(minutes=index * BUCKET_MINUTES)
            fraction = expected_occupancy(room["behavior_profile"], timestamp.hour + timestamp.minute / 60, timestamp.weekday())
            average = int(round(clamp(room["capacity"] * fraction + rng.gauss(0, room["capacity"] * 0.035), 0, room["capacity"])))
            minimum = max(0, min(average, average - rng.randint(0, max(1, round(room["capacity"] * 0.08)))))
            maximum = min(room["capacity"], max(average, average + rng.randint(0, max(1, round(room["capacity"] * 0.08)))))
            rows.append({
                "room_id": room["room_id"],
                "camera_id": room["camera_id"],
                "bucket_start": iso(timestamp),
                "timestamp": iso(timestamp),
                "avg_occupancy": average,
                "min_occupancy": minimum,
                "max_occupancy": maximum,
                "capacity_snapshot": room["capacity"],
                "coverage_percentage": round(100.0, 2),
            })
    return rows


def make_live(rng: random.Random, now: datetime) -> dict[str, Any]:
    statuses = {
        "cam_001": "online", "cam_002": "online", "cam_003": "stale",
        "cam_004": "online", "cam_005": "online", "cam_006": "offline",
        "cam_007": "online", "cam_008": "online", "cam_009": "online",
        "cam_010": "online", "cam_011": "online", "cam_012": "online",
        "cam_013": "online", "cam_014": "online", "cam_015": "online",
        "cam_016": "online", "cam_017": "online", "cam_018": "online",
        "cam_019": "online", "cam_020": "online",
    }
    results = []
    for room in ROOMS:
        status = statuses[room["camera_id"]]
        percentage = expected_occupancy(room["behavior_profile"], 13.0, now.weekday())
        occupancy = int(round(clamp(room["capacity"] * percentage + rng.gauss(0, 2), 0, room["capacity"])))
        updated = now - timedelta(minutes=11) if status == "stale" else now
        if status == "offline":
            occupancy = 0
        results.append({"camera_id": room["camera_id"], "occupancy": occupancy, "updated_at": iso(updated), "status": status})
    return {"cameras": results}


def make_room_views(live: dict[str, Any], now: datetime) -> list[dict[str, Any]]:
    by_camera = {item["camera_id"]: item for item in live["cameras"]}
    views = []
    for room in ROOMS:
        item = by_camera[room["camera_id"]]
        percentage = round(item["occupancy"] / room["capacity"] * 100, 2) if room["capacity"] else 0.0
        views.append({**room, "current_occupancy": item["occupancy"], "occupancy_percentage": percentage, "intensity": intensity(percentage), "status": item["status"], "updated_at": item["updated_at"]})
    return views


def derive_history_views(rows: list[dict[str, Any]], room_id: str | None = None) -> dict[str, Any]:
    selected = [row for row in rows if room_id is None or row["room_id"] == room_id]
    def aggregate(key: str, metric: str) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        first_timestamp = min((datetime.fromisoformat(row["bucket_start"].replace("Z", "+00:00")) for row in selected), default=None)
        week_anchor = first_timestamp.replace(hour=0, minute=0, second=0, microsecond=0) if first_timestamp else None
        for row in selected:
            timestamp = datetime.fromisoformat(row["bucket_start"].replace("Z", "+00:00"))
            if key == "hour":
                group = timestamp.replace(minute=0, second=0, microsecond=0)
            elif key == "day":
                group = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                group = week_anchor
            grouped.setdefault(iso(group), []).append(row)
        values = []
        for bucket, items in sorted(grouped.items()):
            average_occupancy = sum(item["avg_occupancy"] for item in items) / len(items)
            if metric == "percentage":
                capacity = sum(item["capacity_snapshot"] for item in items) / len(items)
                value = average_occupancy / capacity * 100 if capacity else 0.0
            else:
                value = average_occupancy
            values.append({"bucket_start": bucket, "value": round(value, 4)})
        return values
    return {"occupancy": {"hour": aggregate("hour", "occupancy"), "day": aggregate("day", "occupancy"), "week": aggregate("week", "occupancy")}, "percentage": {"hour": aggregate("hour", "percentage"), "day": aggregate("day", "percentage"), "week": aggregate("week", "percentage")}}


def generate(output_dir: Path, start: datetime = DEFAULT_START, seed: int = SEED) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    history = generate_history(rng, start)
    now = start + timedelta(days=HISTORY_DAYS, hours=13)
    live = make_live(rng, now)
    rooms = make_room_views(live, now)

    # Explicit fixtures make failure handling testable without corrupting normal history invariants.
    edge_cases = {
        "stale_camera": {"camera_id": "cam_003", "status": "stale", "updated_at": iso(now - timedelta(minutes=11)), "stale_after_minutes": 10},
        "offline_camera": {"camera_id": "cam_006", "status": "offline", "occupancy": 0},
        "zero_occupancy": {"room_id": "room_library_02", "bucket_start": iso(start + timedelta(days=5, hours=2)), "avg_occupancy": 0, "min_occupancy": 0, "max_occupancy": 0, "capacity_snapshot": 12, "coverage_percentage": 100.0},
        "very_high_occupancy": {"room_id": "room_canteen", "bucket_start": iso(start + timedelta(days=2, hours=13)), "avg_occupancy": 119, "min_occupancy": 112, "max_occupancy": 120, "capacity_snapshot": 120, "coverage_percentage": 100.0},
        "missing_history": {"room_id": "room_ece_105", "from": iso(start + timedelta(days=4, hours=3)), "to": iso(start + timedelta(days=4, hours=4)), "reason": "camera_upload_gap"},
        "partial_coverage_bucket": {"room_id": "room_cse_202", "bucket_start": iso(start + timedelta(days=3, hours=9, minutes=15)), "avg_occupancy": 18, "min_occupancy": 16, "max_occupancy": 20, "capacity_snapshot": 35, "coverage_percentage": 62.5},
        "over_capacity_model_server": {"camera_id": "cam_005", "occupancy": 126, "updated_at": iso(now), "status": "online", "configured_capacity": 120, "expected_backend_behavior": "cap display percentage at 100 while retaining raw model value for diagnostics"},
    }
    views = {"range": {"hour": {}, "day": {}, "week": {}}, "metric": {"occupancy": {}, "percentage": {}}}
    for room in ROOMS:
        derived = derive_history_views(history, room["room_id"])
        for range_name in ("hour", "day", "week"):
            views["range"][range_name][room["room_id"]] = {"metric": {"occupancy": derived["occupancy"][range_name], "percentage": derived["percentage"][range_name]}}
        for metric in ("occupancy", "percentage"):
            views["metric"][metric][room["room_id"]] = {"range": {name: derived[metric][name] for name in ("hour", "day", "week")}}

    artifacts = {
        "rooms.json": {"generated_at": iso(now), "seed": seed, "rooms": ROOMS},
        "history_5min_7days.json": {"generated_at": iso(now), "seed": seed, "bucket_minutes": BUCKET_MINUTES, "history_days": HISTORY_DAYS, "records": history},
        "live_occupancy.json": live,
        "room_views.json": {"generated_at": iso(now), "rooms": rooms},
        "historical_api_views.json": {"generated_at": iso(now), "description": "API-ready range/metric views derived from 5-minute source history", "views": views},
        "edge_cases.json": {"generated_at": iso(now), "cases": edge_cases},
    }
    for filename, payload in artifacts.items():
        (output_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(artifacts)} artifacts in {output_dir} using seed {seed}.")
    print(f"History records: {len(history)} ({len(ROOMS)} rooms x {HISTORY_DAYS * 24 * 60 // BUCKET_MINUTES} buckets)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OccupAI deterministic mock data")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("generated"))
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--start", type=lambda value: datetime.fromisoformat(value.replace("Z", "+00:00")), default=DEFAULT_START)
    args = parser.parse_args()
    generate(args.output_dir, args.start, args.seed)
