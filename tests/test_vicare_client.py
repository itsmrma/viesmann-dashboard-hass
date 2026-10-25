import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from addon.viesmann_dashboard.viesmann_dashboard.app import fetch_vicare_entities


class VicareClientTests(unittest.TestCase):
    def test_reads_only_selected_entities_from_home_assistant(self):
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                seen.append((self.command, self.path, self.headers.get("Authorization")))
                payload = [
                    {"entity_id": "sensor.vicare_flow", "state": "34.8", "last_updated": "2026-10-25T10:00:00+00:00", "attributes": {"friendly_name": "Flow", "unit_of_measurement": "°C", "secret": "discard"}},
                    {"entity_id": "switch.heater", "state": "on", "attributes": {}},
                ]
                body = json.dumps(payload).encode()
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

        result = fetch_vicare_entities(
            ["sensor.vicare_flow"], "local-test-token",
            api_url=f"http://127.0.0.1:{server.server_port}/api/states",
        )

        self.assertEqual(seen, [("GET", "/api/states", "Bearer local-test-token")])
        self.assertEqual(result, [{
            "entity_id": "sensor.vicare_flow",
            "state": "34.8",
            "last_updated": "2026-10-25T10:00:00+00:00",
            "attributes": {"friendly_name": "Flow", "unit_of_measurement": "°C"},
        }])


if __name__ == "__main__":
    unittest.main()
