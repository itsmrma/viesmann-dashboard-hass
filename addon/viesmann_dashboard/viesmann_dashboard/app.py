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
    }


def fetch_vicare_entities(
    token: str | None,
    api_url: str = "http://supervisor/core/api/states",
    websocket_url: str = "ws://supervisor/core/websocket",
    websocket_connector=None,
) -> list[dict]:
    if not token:
        raise RuntimeError("Home Assistant API token is unavailable")
    if websocket_connector is None:
        from websocket import create_connection

        websocket_connector = create_connection

    connection = websocket_connector(websocket_url, timeout=10)
    try:
        greeting = json.loads(connection.recv())
        if greeting.get("type") != "auth_required":
            raise RuntimeError("Home Assistant WebSocket did not request authentication")
        connection.send(json.dumps({"type": "auth", "access_token": token}))
        auth_result = json.loads(connection.recv())
        if auth_result.get("type") != "auth_ok":
            raise RuntimeError("Home Assistant WebSocket authentication failed")
        connection.send(json.dumps({"id": 1, "type": "config/entity_registry/list"}))
        registry_result = json.loads(connection.recv())
        if registry_result.get("type") != "result" or not registry_result.get("success"):
            raise RuntimeError("Home Assistant could not list the entity registry")
        entity_ids = {
            entry["entity_id"]
            for entry in registry_result.get("result", [])
            if entry.get("platform") == "vicare"
            and entry.get("disabled_by") is None
            and entry.get("entity_id", "").split(".", 1)[0]
            in {"sensor", "binary_sensor", "climate", "water_heater"}
        }
    finally:
        connection.close()

    if not entity_ids:
        return []
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
    return [
        {
            "entity_id": entity["entity_id"],
            "state": entity.get("state", "unknown"),
            "last_updated": entity.get("last_updated"),
            "attributes": {
                key: entity.get("attributes", {}).get(key)
                for key in (
                    "friendly_name", "unit_of_measurement", "device_class",
                    "current_temperature", "temperature", "current_humidity", "hvac_action",
                )
                if entity.get("attributes", {}).get(key) is not None
            },
        }
        for entity in states
        if entity.get("entity_id") in entity_ids
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
            entities = fetch_vicare_entities(token)
            if not entities:
                raise RuntimeError("No enabled ViCare reading entities were found in Home Assistant")
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
