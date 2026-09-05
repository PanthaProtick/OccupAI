from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from backend.auth import AuthError


class AuthenticationRateLimiter:
    """Small process-local sliding-window limiter for authentication endpoints."""

    def __init__(self, attempts: int, window_seconds: int):
        self.attempts = attempts
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.attempts:
                raise AuthError(429, "rate_limit_exceeded", "Too many attempts. Please try again later.")
            events.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._events.pop(key, None)
