"""Runtime entry point for the Supervisor add-on."""

from __future__ import annotations

import json
import os
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .client_2701 import ControllerClient
from .server import make_handler
from .state import DashboardState


def read_options(path: str = "/data/options.json") -> dict:
    with open(path, encoding="utf-8") as options_file:
        options = json.load(options_file)
    minutes = int(options.get("poll_minutes", 2))
    if not 1 <= minutes <= 60:
        raise ValueError("poll_minutes must be between 1 and 60")
    return {
        "controller_url": str(options.get("controller_url", "")).rstrip("/"),
        "session_cookie": str(options.get("session_cookie", "")),
        "poll_seconds": minutes * 60,
        "vicare_entities": [value.strip() for value in str(options.get("vicare_entities", "")).split(",") if value.strip()],
    }


def fetch_vicare_entities(
    entity_ids: list[str], token: str | None,
    api_url: str = "http://supervisor/core/api/states",
) -> list[dict]:
    if not token:
        raise RuntimeError("Home Assistant API token is unavailable")
    request = Request(
        api_url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            states = json.loads(response.read())
    except HTTPError as error:
        if error.code in {401, 403}:
            raise RuntimeError("Home Assistant API authentication failed") from None
        raise RuntimeError(f"Home Assistant API returned HTTP {error.code}") from None
    selected = set(entity_ids)
    return [
        {
            "entity_id": entity["entity_id"],
            "state": entity.get("state", "unknown"),
            "last_updated": entity.get("last_updated"),
            "attributes": {
                key: entity.get("attributes", {}).get(key)
                for key in ("friendly_name", "unit_of_measurement", "device_class")
                if entity.get("attributes", {}).get(key) is not None
            },
        }
        for entity in states
        if entity.get("entity_id") in selected
    ]


def poll_forever(options: dict, state: DashboardState, stop: threading.Event) -> None:
    controller = ControllerClient(options["controller_url"], options["session_cookie"])
    token = os.environ.get("SUPERVISOR_TOKEN")
    while not stop.is_set():
        try:
            if not options["controller_url"] or not options["session_cookie"]:
                raise RuntimeError("Configure the 2701 URL and PHP session cookie in add-on options")
            state.update_2701(controller.fetch_snapshot())
        except Exception:
            state.fail("2701", "2701 poll failed; check URL, PHPSESSID, and controller availability")
        try:
            if not options["vicare_entities"]:
                raise RuntimeError("Configure ViCare entity IDs in add-on options")
            entities = fetch_vicare_entities(options["vicare_entities"], token)
            if not entities:
                raise RuntimeError("No configured ViCare entities were found in Home Assistant")
            state.update_vicare(entities)
        except Exception as error:
            state.fail("vicare", str(error))
        stop.wait(options["poll_seconds"])


def main() -> None:
    from http.server import ThreadingHTTPServer

    options = read_options()
    state = DashboardState(options["poll_seconds"])
    stop = threading.Event()
    threading.Thread(target=poll_forever, args=(options, state, stop), daemon=True).start()
    server = ThreadingHTTPServer(("0.0.0.0", 8099), make_handler(state, enforce_ingress_peer=True))
    try:
        server.serve_forever()
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
