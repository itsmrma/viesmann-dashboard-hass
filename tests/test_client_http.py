import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from addon.viesmann_dashboard.viesmann_dashboard.client_2701 import ControllerClient


class ClientHttpTests(unittest.TestCase):
    def test_reads_index_and_zone_with_session_cookie_using_get(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.command, self.path, self.headers.get("Cookie")))
                if self.path == "/index_refresh.php":
                    body = b"<response><system><hp_season>0</hp_season></system><zones><zone><idx>0</idx><name>Living</name></zone></zones></response>"
                elif self.path == "/zone_refresh.php?ids=0":
                    body = b"<response><zone><idx>0</idx><set_temp>21</set_temp><temp_op>20</temp_op><hum>--.-</hum><term_on_classname>red</term_on_classname></zone></response>"
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
        self.assertEqual(requests, [
            ("GET", "/index_refresh.php", "PHPSESSID=safe-session"),
            ("GET", "/zone_refresh.php?ids=0", "PHPSESSID=safe-session"),
        ])


if __name__ == "__main__":
    unittest.main()
