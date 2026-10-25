"""Small standard-library HTTP server for the Home Assistant Ingress UI."""

import html as html_module
import json
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Type


UI_FILE = Path(__file__).parent / "www" / "index.html"
INGRESS_PROXY = "172.30.32.2"


def make_handler(state, enforce_ingress_peer: bool = False) -> Type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args) -> None:
            return

        def _allowed_peer(self) -> bool:
            return not enforce_ingress_peer or self.client_address[0] == INGRESS_PROXY

        def do_GET(self):
            if not self._allowed_peer():
                self.send_error(403)
                return
            path = self.path.rstrip("/") or "/"
            if path.endswith("/api/status"):
                body = json.dumps(state.snapshot(), ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            ingress_path = self.headers.get("X-Ingress-Path", "").rstrip("/")
            is_ui_path = path in {"/", "/index.html"} or (ingress_path and path == ingress_path)
            if is_ui_path:
                html = UI_FILE.read_text(encoding="utf-8")
                base = f'<base href="{html_module.escape(ingress_path, quote=True)}/">' if ingress_path.startswith("/") else ""
                if base:
                    html = html.replace("</head>", f"{base}</head>", 1)
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404)

    return DashboardHandler
