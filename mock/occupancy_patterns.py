"""Shared synthetic busy-campus patterns for live simulation and mock history.

These are demonstration schedules, not measured usage or opening hours: most
rooms remain in use at any viewing time, with staggered breaks and modest daily
variation. Timestamps stay UTC on the wire; schedules use Bangladesh local time.
"""

import math
import zlib
from datetime import datetime, timedelta, timezone

CAMPUS_TIMEZONE = timezone(timedelta(hours=6), "Asia/Dhaka")


def expected_occupancy(profile: str, hour: float, day: int, room_key: str = "") -> float:
    """Return a bounded fraction with smooth, independently phased quiet spells."""
    if profile not in {"classroom", "library", "study_room", "canteen"}:
        raise ValueError(f"Unknown behavior profile: {profile}")
    # Unlike Python's hash(), this is stable across processes and restarts.
    identity = zlib.crc32((room_key or profile).encode("utf-8"))
    phase = (identity % 10000) / 10000
    classroom = profile == "classroom"
    period = 120 if classroom else 180
    minute = hour * 60
    distance = ((minute + phase * period) % period) - period / 2
    quiet = math.exp(-0.5 * (distance / (8 if classroom else 6)) ** 2)
    baseline = (0.77 if classroom else 0.82) + 0.08 * math.sin(
        2 * math.pi * (minute / 240 + phase)
    )
    daily = 0.025 * math.cos(2 * math.pi * (hour - 13) / 24)
    # Bangladesh's Friday/Saturday weekend is slightly quieter in this demo.
    weekend = 0.025 if day in {4, 5} else 0.0
    return max(0.08, min(0.96, baseline + daily - weekend - 0.60 * quiet))


def occupancy_at(profile: str, timestamp: datetime, room_key: str) -> float:
    if timestamp.tzinfo is None:
        raise ValueError("Occupancy schedules require a timezone-aware timestamp")
    local = timestamp.astimezone(CAMPUS_TIMEZONE)
    hour = local.hour + local.minute / 60 + local.second / 3600
    return expected_occupancy(profile, hour, local.weekday(), room_key)
