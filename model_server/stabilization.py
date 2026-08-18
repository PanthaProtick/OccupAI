from __future__ import annotations

from collections import Counter, deque
import time
from typing import Deque


class OccupancyStabilizer:
    """Return the time-window mode of raw occupancy observations."""

    def __init__(self, window_seconds: float = 2.0) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be greater than zero")
        self.window_seconds = window_seconds
        self.history: Deque[tuple[float, int]] = deque()

    def update(self, count: int, timestamp: float | None = None) -> int:
        if count < 0:
            raise ValueError("occupancy count cannot be negative")
        if timestamp is None:
            timestamp = time.time()

        self.history.append((timestamp, count))
        cutoff = timestamp - self.window_seconds
        while self.history and self.history[0][0] < cutoff:
            self.history.popleft()
        return self.get_stable_count()

    def get_stable_count(self) -> int:
        if not self.history:
            return 0

        frequencies = Counter(count for _, count in self.history)
        max_frequency = max(frequencies.values())
        candidates = {count for count, frequency in frequencies.items() if frequency == max_frequency}

        # Reverse chronological order makes the tie-break deterministic.
        for _, count in reversed(self.history):
            if count in candidates:
                return count
        return self.history[-1][1]

