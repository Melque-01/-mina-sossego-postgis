"""api.py — servidor HTTP só para /api/* . Lógica em handlers.py."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from . import handlers
from .config import mask_dsn
from .db import DSN

ALLOWED_ORIGINS = {"http://localhost:8000", "http://127.0.0.1:8000"}


class APIHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    # --- headers ---
    def _cors(self):
        o = self.headers.get("Origin", "")
        if o in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")

    def _sec(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", "default-src 'none'")

    def _json(self, dados, status=200):
        corpo = json.dumps(dados, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self._cors()
        self._sec()
        self.end_headers()
        self.wfile.write(corpo)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self._sec()
        self.end_headers()

    # --- dispatcher único ---
    def _handle(self, method: str):
        rota = urlparse(self.path)
        path, query = rota.path, rota.query

        # só responde /api/*
        if not path.startswith("/api/"):
            return self._json({"erro": "Nao encontrado"}, 404)

        # body para POST
        body = None
        if method == "POST":
            n = int(self.headers.get("Content-Length", 0) or 0)
            raw = self.rfile.read(n) if n else b"{}"
            try:
                body = json.loads(raw or b"{}")
            except Exception:
                return self._json({"erro": "JSON invalido"}, 400)

        res = handlers.dispatch(method, path, self.headers, query, body)
        if res is None:
            return self._json({"erro": "Nao encontrado"}, 404)
        dados, status = res
        return self._json(dados, status)

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def run(host="127.0.0.1", port=8001):
    print(f"[api] http://{host}:{port}/  DSN {mask_dsn(DSN)}")
    print("[api] só /api/* | CORS -> localhost:8000")
    HTTPServer((host, port), APIHandler).serve_forever()


if __name__ == "__main__":
    run()
