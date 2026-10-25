import json
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from addon.viesmann_dashboard.viesmann_dashboard.server import make_handler
from addon.viesmann_dashboard.viesmann_dashboard.state import DashboardState


class DashboardApiTests(unittest.TestCase):
    def test_status_exposes_readings_and_source_freshness(self):
        now = datetime.now(timezone.utc)
        state = DashboardState(poll_seconds=120, clock=lambda: now)
        state.update_2701({"season": "winter", "zones": []}, now - timedelta(seconds=10))
        state.update_vicare([{"entity_id": "sensor.vicare_flow", "state": "34.8", "last_updated": now.isoformat()}], now)
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        with urlopen(f"http://127.0.0.1:{server.server_port}/api/status") as response:
            body = json.loads(response.read())

        self.assertEqual(body["sources"]["2701"]["status"], "fresh")
        self.assertEqual(body["sources"]["vicare"]["status"], "fresh")
        self.assertEqual(body["2701"]["season"], "winter")

    def test_vicare_staleness_uses_entity_update_time_and_keeps_last_reading(self):
        now = datetime.now(timezone.utc)
        state = DashboardState(poll_seconds=120, clock=lambda: now)
        state.update_vicare([
            {
                "entity_id": "sensor.vicare_flow",
                "state": "34.8",
                "last_updated": now.isoformat(),
                "attributes": {},
            },
            {
                "entity_id": "sensor.vicare_return",
                "state": "29.1",
                "last_updated": (now - timedelta(minutes=5)).isoformat(),
                "attributes": {},
            },
        ])

        snapshot = state.snapshot()

        self.assertEqual(snapshot["sources"]["vicare"]["status"], "stale")
        self.assertEqual(snapshot["vicare"][0]["state"], "34.8")
        self.assertEqual(snapshot["vicare"][1]["state"], "29.1")

    def test_ingress_ui_uses_the_home_assistant_proxy_base_path(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(DashboardState(poll_seconds=120)))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            f"http://127.0.0.1:{server.server_port}/api/hassio_ingress/test-addon",
            headers={"X-Ingress-Path": "/api/hassio_ingress/test-addon"},
        )

        with urlopen(request) as response:
            html = response.read().decode()

        self.assertIn('<base href="/api/hassio_ingress/test-addon/">', html)
        self.assertIn("fetch('api/status'", html)
        self.assertNotIn("<button", html)
        self.assertNotIn("<form", html)

    def test_read_only_api_rejects_mutating_methods(self):
        state = DashboardState(poll_seconds=120)
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        from urllib.error import HTTPError
        request = __import__("urllib.request", fromlist=["Request"]).Request(
            f"http://127.0.0.1:{server.server_port}/api/status", method="POST"
        )
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 501)


if __name__ == "__main__":
    unittest.main()
