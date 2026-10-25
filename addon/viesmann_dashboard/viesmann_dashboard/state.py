"""Thread-safe, read-only dashboard snapshot and freshness tracking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any, Callable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class DashboardState:
    def __init__(self, poll_seconds: int, clock: Callable[[], datetime] = utc_now):
        self.poll_seconds = poll_seconds
        self._clock = clock
        self._lock = Lock()
        self._data: dict[str, Any] = {"2701": None, "vicare": None}
        self._updated: dict[str, datetime | None] = {"2701": None, "vicare": None}
        self._errors: dict[str, str | None] = {"2701": None, "vicare": None}

    def update_2701(self, data: dict[str, Any], at: datetime | None = None) -> None:
        with self._lock:
            self._data["2701"] = data
            self._updated["2701"] = at or self._clock()
            self._errors["2701"] = None

    def update_vicare(self, data: list[dict[str, Any]], at: datetime | None = None) -> None:
        entity_updates = []
        for entity in data:
            value = entity.get("last_updated")
            if not value:
                continue
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                entity_updates.append(parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc))
            except (TypeError, ValueError):
                continue
        source_updated = min(entity_updates) if entity_updates else (at or self._clock())
        with self._lock:
            self._data["vicare"] = data
            self._updated["vicare"] = source_updated
            self._errors["vicare"] = None

    def fail(self, source: str, error: str) -> None:
        with self._lock:
            self._errors[source] = error

    def snapshot(self) -> dict[str, Any]:
        now = self._clock()
        stale_after = timedelta(seconds=self.poll_seconds * 2)
        with self._lock:
            result = {"2701": self._data["2701"], "vicare": self._data["vicare"]}
            sources = {}
            for key in ("2701", "vicare"):
                updated = self._updated[key]
                status = "unavailable" if updated is None else (
                    "stale" if now - updated > stale_after else "fresh"
                )
                sources[key] = {
                    "status": status,
                    "last_updated": _iso(updated),
                    "error": self._errors[key],
                }
            return {"2701": result["2701"], "vicare": result["vicare"], "sources": sources}
