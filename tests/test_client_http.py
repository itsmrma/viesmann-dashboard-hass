import threading
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import Mock
from http.server import BaseHTTPRequestHandler, HTTPServer

from addon.viesmann_dashboard.viesmann_dashboard.client_2701 import ControllerClient


class ClientHttpTests(unittest.TestCase):
    def test_summary_activity_is_authoritative_with_a_detail_fallback(self):
        for summary, detail, expected in [("gray", "red", False), ("blue", "gray", True),
                                           (None, "red", True), (None, None, None)]:
            with self.subTest(summary=summary, detail=detail):
                indicator = lambda value: f"<term_on_classname>{value}</term_on_classname>" if value else ""
                client = ControllerClient("http://controller", "session")
                client._get_xml = Mock(side_effect=[
                    ET.fromstring(f"<response><zone><idx>0</idx>{indicator(summary)}</zone></response>"),
                    ET.fromstring(f"<response><zone><idx>0</idx>{indicator(detail)}</zone></response>"),
                ])
                self.assertIs(client.fetch_snapshot()["zones"][0]["active"], expected)

    def test_reads_index_and_zone_with_session_cookie_using_get(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.command, self.path, self.headers.get("Cookie")))
                if self.path == "/index_refresh.php":
                    body = b"<response><system><hp_season>0</hp_season></system><zones><zone><idx>0</idx><name>Living</name><term_on_classname>red</term_on_classname></zone></zones></response>"
                elif self.path == "/zone_refresh.php?ids=0":
                    body = b"<response><zone><idx>0</idx><set_temp>21</set_temp><temp_op>20</temp_op><hum>--.-</hum></zone></response>"
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/xml")
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
        client = ControllerClient(f"http://127.0.0.1:{server.server_port}", "safe-session")

        result = client.fetch_snapshot()

        self.assertEqual(result["season"], "winter")
        self.assertEqual(result["zones"][0]["target_temperature"], 21.0)
        self.assertIsNone(result["zones"][0]["humidity"])
        self.assertTrue(result["zones"][0]["active"])
        self.assertEqual(requests, [
            ("GET", "/index_refresh.php", "PHPSESSID=safe-session"),
            ("GET", "/zone_refresh.php?ids=0", "PHPSESSID=safe-session"),
        ])


if __name__ == "__main__":
    unittest.main()
