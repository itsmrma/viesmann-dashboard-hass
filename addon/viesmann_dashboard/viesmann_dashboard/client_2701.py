"""Read-only parsing for the Viessmann 2701 PHP/XML interface."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any


def _number(value: str | None) -> float | None:
    if not value or value.strip() in {"", "--.-", "--"}:
        return None
    try:
        return float(value.strip().replace(",", "."))
    except ValueError:
        return None


def _text(parent: ET.Element, name: str) -> str | None:
    node = parent.find(name)
    if node is None or node.text is None:
        return None
    return node.text.strip()


_ACTIVE_TOKENS = {"red", "blue", "on", "active", "heating", "cooling"}
_INACTIVE_TOKENS = {"gray", "grey", "off", "inactive", "idle"}


def _activity(zone: ET.Element) -> bool | None:
    """Return zone activity from any controller indicator, or None if unknown.

    Firmware variants expose the indicator as ``term_on_classname`` or under a
    similarly named element, so every ``*classname`` and ``term_on*`` child is
    inspected. Active wins over inactive when several indicators disagree.
    """
    tokens: set[str] = set()
    numeric: list[float] = []
    for child in zone:
        tag = child.tag.lower()
        if not (tag.endswith("classname") or tag.startswith("term_on")):
            continue
        value = (child.text or "").strip().lower()
        tokens.update(value.replace("-", " ").replace("_", " ").split())
        if tag.startswith("term_on") and not tag.endswith("classname"):
            parsed = _number(value)
            if parsed is not None:
                numeric.append(parsed)
    if tokens & _ACTIVE_TOKENS or any(value > 0 for value in numeric):
        return True
    if tokens & _INACTIVE_TOKENS or numeric:
        return False
    return None

def parse_controller_xml(payload: str) -> dict[str, Any]:
    """Parse an index_refresh.php XML response into display-safe readings."""
    root = ET.fromstring(payload)
    system = root.find(".//system")
    season_code = _text(system, "hp_season") if system is not None else None
    season = {"0": "winter", "1": "summer"}.get(season_code)

    zones: list[dict[str, Any]] = []
    for zone in root.findall(".//zone"):
        identifier = _text(zone, "idx")
        try:
            zone_id = int(identifier) if identifier is not None else None
        except ValueError:
            zone_id = None
        zones.append({
            "id": zone_id,
            "name": _text(zone, "name"),
            "room_temperature": _number(_text(zone, "temp_op")),
            "target_temperature": _number(_text(zone, "set_temp")),
            "humidity": _number(_text(zone, "hum")),
            "active": _activity(zone),
        })
    return {"season": season, "zones": zones}


class ControllerClient:
    """Fetch controller readings through its read-only PHP/XML GET endpoints."""

    def __init__(self, base_url: str, session_cookie: str, timeout: float = 10.0):
        from urllib.request import Request, urlopen

        self._request = Request
        self._urlopen = urlopen
        self._base_url = base_url.rstrip("/")
        self._session_cookie = session_cookie
        self._timeout = timeout

    def _get_xml(self, path: str) -> ET.Element:
        request = self._request(
            f"{self._base_url}/{path}",
            headers={"Cookie": f"PHPSESSID={self._session_cookie}", "Accept": "application/xml"},
            method="GET",
        )
        with self._urlopen(request, timeout=self._timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"2701 returned HTTP {response.status}")
            return ET.fromstring(response.read())

    def fetch_snapshot(self) -> dict[str, Any]:
        index = self._get_xml("index_refresh.php")
        system = index.find(".//system")
        season_code = _text(system, "hp_season") if system is not None else None
        season = {"0": "winter", "1": "summer"}.get(season_code)
        zones: list[dict[str, Any]] = []
        for summary in index.findall(".//zone"):
            identifier = _text(summary, "idx")
            if identifier is None:
                continue
            details = self._get_xml(f"zone_refresh.php?ids={identifier}")
            zone = details.find(".//zone")
            if zone is None:
                continue
            # The overview owns the seasonal activity indicator. Some firmware
            # omits it from zone_refresh.php, which supplies detailed readings.
            active = _activity(summary)
            if active is None:
                active = _activity(zone)
            try:
                zone_id = int(identifier)
            except ValueError:
                zone_id = None
            zones.append({
                "id": zone_id,
                "name": _text(summary, "name"),
                "room_temperature": _number(_text(zone, "temp_op")),
                "target_temperature": _number(_text(zone, "set_temp")),
                "humidity": _number(_text(zone, "hum")),
                "active": active,
            })
        return {"season": season, "zones": zones}
