"""frontend.py — serve web/ e proxy /api -> backend:8001. Fallback usa handlers."""
import http.client
import json
from http.server import SimpleHTTPRequestHandler
from urllib.parse import urlparse

BACKEND_HOST, BACKEND_PORT = "127.0.0.1", 8001


class FrontendHandler(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        super().end_headers()

    def _is_api(self):
        return self.path.startswith("/api/")

    # tenta backend, se falhar usa handlers local
    def _proxy(self):
        headers_fwd = {k: v for k, v in self.headers.items() if k.lower() in ("content-type", "authorization", "content-length")}
        body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) if self.command in ("POST", "PUT") else None
        if body and "Content-Length" not in headers_fwd:
            headers_fwd["Content-Length"] = str(len(body))
        try:
            conn = http.client.HTTPConnection(BACKEND_HOST, BACKEND_PORT, timeout=5)
            conn.request(self.command, self.path, body=body, headers=headers_fwd)
            resp = conn.getresponse()
            data = resp.read()
            self.send_response(resp.status)
            for h, v in resp.getheaders():
                if h.lower() in ("content-type", "content-length", "access-control-allow-origin", "vary"):
                    self.send_header(h, v)
            self.send_header("X-Proxy-By", "frontend.py")
            self.end_headers()
            if data:
                self.wfile.write(data)
            conn.close()
            return True
        except Exception:
            return self._fallback(body)

    def _fallback(self, body=None):
        from backend import handlers

        rota = urlparse(self.path)
        path, query, method = rota.path, rota.query, self.command

        # body p/ POST (se não veio do _proxy)
        json_body = None
        if method == "POST":
            raw = body if body is not None else (self.rfile.read(int(self.headers.get("Content-Length", 0) or 0)) or b"{}")
            try:
                json_body = json.loads(raw or b"{}")
            except Exception:
                return self._send({"erro": "JSON invalido"}, 400)

        res = handlers.dispatch(method, path, self.headers, query, json_body)
        if res is None:
            return False  # não é /api/* -> serve arquivo estático
        dados, status = res
        # marca fallback
        if isinstance(dados, dict):
            dados = {**dados, "_via": "fallback"} if status == 200 and path == "/api/health" else dados
        return self._send(dados, status)

    def _send(self, dados, status=200):
        corpo = json.dumps(dados, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)
        return True

    def do_GET(self):
        if self._is_api() and self._proxy():
            return
        return super().do_GET()

    def do_POST(self):
        if self._is_api() and self._proxy():
            return
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"erro":"Nao encontrado"}')

    def do_OPTIONS(self):
        if self._is_api():
            self._proxy()
            return
        super().do_OPTIONS()
