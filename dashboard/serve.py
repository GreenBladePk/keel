"""Standalone static server for the Keel dashboard (no deps).
Run: python keel/dashboard/serve.py   (PORT env, default 8050)"""
import http.server
import os
import socketserver

PORT = int(os.environ.get("PORT", "8050"))
DIR = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=DIR, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"Keel dashboard on http://localhost:{PORT}  (serving {DIR})")
        httpd.serve_forever()
