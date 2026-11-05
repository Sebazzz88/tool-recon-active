#!/usr/bin/env python3
"""Laboratorio VULNERABLE para las pruebas del scanner.

Simula de forma determinista fallos de: SQLi (error/boolean/POST), XSS
reflejado, SSTI, SSRF, CMDi (output), LFI y Host Header injection.
NO es la herramienta; es un objetivo de laboratorio local y autorizado.
"""
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PAGE = ("<html><head><script src='/app.js'></script>"
        "<script>var x=1;</script></head><body>"
        "<h1>Lab</h1><p>contenido normal relleno relleno relleno</p>"
        "Echo: {echo}</body></html>")

PASSWD = ("root:x:0:0:root:/root:/bin/bash\n"
          "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n")


def build_body(params):
    echo = ""
    for _k, vals in params.items():
        for v in vals:
            lv = v.lower()
            # SQLi error-based: comilla provoca "error SQL"
            if "'" in v and "AND" not in v.upper():
                return "You have an error in your SQL syntax; check your MySQL"
            # SQLi boolean: longitudes distintas segun 1=1 vs 1=2
            if "'1'='1" in v:
                return PAGE.format(echo="VERDADERO " + "A" * 300)
            if "'1'='2" in v:
                return PAGE.format(echo="FALSO")
            # SSTI: {{7*7}} se evalua a 49 (sin reflejar el payload)
            if "{{7*7}}" in v or "${7*7}" in v:
                return PAGE.format(echo="49")
            # SSRF: metadata cloud -> indicador fuerte
            if "169.254.169.254" in v:
                return "instance-id: i-0123456789 ami-id: ami-xyz"
            # CMDi output-based: simula salida de 'id'
            if "sleep" in lv:
                return "uid=0(root) gid=0(root) groups=0(root)"
            # LFI: lectura de /etc/passwd
            if "etc/passwd" in lv or "etc%2fpasswd" in lv:
                return PASSWD
            echo += v
    return PAGE.format(echo=echo)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _host_header_vuln(self):
        # Host Header injection: refleja Host/X-Forwarded-Host como URL absoluta
        for h in ("Host", "X-Forwarded-Host", "X-Forwarded-Server"):
            val = self.headers.get(h, "")
            if "evil.com" in val.lower():
                return True
        return False

    def _respond(self, params):
        if self._host_header_vuln():
            body = f'<a href="https://evil.com/reset">link</a>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body.encode())
            return
        body = build_body(params)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_GET(self):
        self._respond(parse_qs(urlparse(self.path).query))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode(errors="ignore")
        self._respond(parse_qs(raw))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
