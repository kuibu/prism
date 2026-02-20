"""Agent tool gateway helpers."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock


class InMemoryRateCounter:
    """Tracks per-key request counts in a rolling time window."""

    def __init__(self, *, window_seconds: int = 60) -> None:
        self.window_seconds = max(1, window_seconds)
        self._events: dict[str, deque[datetime]] = {}
        self._lock = Lock()

    def increment_and_count(self, key: str, *, now: datetime | None = None) -> int:
        ts = now.astimezone(timezone.utc) if now is not None else datetime.now(timezone.utc)
        cutoff = ts - timedelta(seconds=self.window_seconds)

        with self._lock:
            bucket = self._events.setdefault(key, deque())
            bucket.append(ts)
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            return len(bucket)
