#!/usr/bin/env python3
"""Servidor SEGURO: codifica la entrada (sin reflexion), longitud constante,
sin errores SQL, sin metadata, sin salida de comandos. Sirve para verificar
que los modulos NO generan falsos positivos."""
import sys, html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PAGE = ("<html><head><script src='/a.js'></script><script>var x=1;</script>"
        "</head><body><h1>Seguro</h1><p>contenido fijo de relleno constante "
        "para que la longitud no cambie con el input</p>Echo: {echo}</body></html>")

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _r(self, params):
        echo = ""
        for k, vals in params.items():
            for v in vals:
                echo += html.escape(v)  # entrada SIEMPRE codificada -> sin reflexion
        # longitud constante: recorto/relleno el echo a 40 chars
        echo = (echo[:40]).ljust(40, ".")
        body = PAGE.format(echo=echo)
        self.send_response(200)
        self.send_header("Content-Type", "text/html"); self.end_headers()
        self.wfile.write(body.encode())
    def do_GET(self): self._r(parse_qs(urlparse(self.path).query))
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self._r(parse_qs(self.rfile.read(n).decode(errors="ignore")))

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
