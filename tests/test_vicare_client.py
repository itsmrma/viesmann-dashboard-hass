import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from addon.viesmann_dashboard.viesmann_dashboard.app import fetch_vicare_entities


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.replies = [
            {"type": "auth_required"},
            {"type": "auth_ok"},
            {
                "id": 1,
                "type": "result",
                "success": True,
                "result": [
                    {"entity_id": "sensor.vicare_flow", "platform": "vicare", "disabled_by": None},
                    {"entity_id": "climate.vicare_heating", "platform": "vicare", "disabled_by": None},
                    {"entity_id": "button.vicare_charge", "platform": "vicare", "disabled_by": None},
                    {"entity_id": "sensor.other_flow", "platform": "other", "disabled_by": None},
                    {"entity_id": "sensor.vicare_disabled", "platform": "vicare", "disabled_by": "user"},
                ],
            },
        ]

    def recv(self):
        return json.dumps(self.replies.pop(0))

    def send(self, payload):
        self.sent.append(json.loads(payload))

    def close(self):
        pass


class VicareClientTests(unittest.TestCase):
    def test_discovers_enabled_reading_entities_and_fetches_their_states(self):
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append((self.command, self.path, self.headers.get("Authorization")))
                body = json.dumps([
                    {"entity_id": "sensor.vicare_flow", "state": "34.8", "last_updated": "2026-10-25T10:00:00+00:00", "attributes": {"friendly_name": "Flow", "unit_of_measurement": "°C", "secret": "discard"}},
                    {"entity_id": "climate.vicare_heating", "state": "heat", "last_updated": "2026-10-25T10:01:00+00:00", "attributes": {"friendly_name": "Heating", "current_temperature": 20.5, "secret": "discard"}},
                    {"entity_id": "button.vicare_charge", "state": "unknown", "attributes": {}},
                    {"entity_id": "sensor.other_flow", "state": "99", "attributes": {}},
                ]).encode()
                self.send_response(200)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        websocket = FakeWebSocket()
        connection_args = []

        def connect(url, timeout):
            connection_args.append((url, timeout))
            return websocket

        result = fetch_vicare_entities(
            "local-test-token",
            api_url=f"http://127.0.0.1:{server.server_port}/api/states",
            websocket_url="ws://127.0.0.1:8123/api/websocket",
            websocket_connector=connect,
        )

        self.assertEqual(connection_args, [("ws://127.0.0.1:8123/api/websocket", 10)])
        self.assertEqual([message["type"] for message in websocket.sent], ["auth", "config/entity_registry/list"])
        self.assertEqual(websocket.sent[0]["access_token"], "local-test-token")
        self.assertEqual(seen, [("GET", "/api/states", "Bearer local-test-token")])
        self.assertEqual([entity["entity_id"] for entity in result], ["sensor.vicare_flow", "climate.vicare_heating"])
        self.assertEqual(result[0]["attributes"], {"friendly_name": "Flow", "unit_of_measurement": "°C"})
        self.assertEqual(result[1]["attributes"], {"friendly_name": "Heating", "current_temperature": 20.5})


if __name__ == "__main__":
    unittest.main()
