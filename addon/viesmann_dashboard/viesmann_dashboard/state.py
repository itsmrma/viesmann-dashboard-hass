"""Thread-safe, read-only dashboard snapshot and freshness tracking."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
import math
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
        self._history = {source: deque(maxlen=1440) for source in self._data}

    def _record(self, source: str, at: datetime, readings: list[dict]) -> None:
        self._history[source].append({"at": _iso(at.astimezone(timezone.utc)), "readings": readings})
        self._prune_history(self._clock())

    def _prune_history(self, now: datetime) -> None:
        cutoff = _iso(now.astimezone(timezone.utc) - timedelta(hours=24))
        for samples in self._history.values():
            while samples and samples[0]["at"] < cutoff:
                samples.popleft()

    def update_2701(self, data: dict[str, Any], at: datetime | None = None) -> None:
        with self._lock:
            self._data["2701"] = data
            self._updated["2701"] = at or self._clock()
            self._errors["2701"] = None
            self._record("2701", self._updated["2701"], [dict(zone) for zone in data.get("zones", [])])

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
            readings = []
            for entity in data:
                try:
                    value = float(entity.get("state", ""))
                except (TypeError, ValueError):
                    value = None
                readings.append({
                    "id": entity.get("entity_id"),
                    "value": value if value is not None and math.isfinite(value) else None,
                    "unit": entity.get("attributes", {}).get("unit_of_measurement"),
                })
            self._record("vicare", at or self._clock(), readings)

    def fail(self, source: str, error: str) -> None:
        with self._lock:
            self._errors[source] = error

    def snapshot(self) -> dict[str, Any]:
        now = self._clock()
        stale_after = timedelta(seconds=self.poll_seconds * 2)
        with self._lock:
            self._prune_history(now)
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
            return {"2701": result["2701"], "vicare": result["vicare"], "sources": sources,
                    "history": {source: list(samples) for source, samples in self._history.items()}}
