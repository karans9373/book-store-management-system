from __future__ import annotations

import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"


class SpaHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        requested = self.translate_path(self.path.split("?", 1)[0])
        if self.path.startswith("/api/"):
            self.send_error(404, "API not served here")
            return
        if os.path.exists(requested) and not os.path.isdir(requested):
            return super().do_GET()
        self.path = "/index.html"
        return super().do_GET()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5500), partial(SpaHandler, directory=str(FRONTEND_DIR)))
    print("Frontend running on http://127.0.0.1:5500")
    server.serve_forever()
