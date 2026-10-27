#!/usr/bin/env python3
"""Lokaler Test-Proxy: 127.0.0.1:28766 -> SSH-Tunnel 127.0.0.1:28765 (-> Portal :18765).
Setzt die Header, die sonst Authelia/Caddy setzen. Nur fuer Staging-Tests. Key wird nie ausgegeben."""
import http.client, http.server, socketserver, subprocess, os, sys

KEY = subprocess.run(
    ["ssh", "-i", os.path.expanduser("~/.ssh/hermes_mahome"), "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
     "andrew@ma-server", "python3 -c \"import json;print(json.load(open('/etc/ma-home/portal.json'))['proxy_key'])\""],
    capture_output=True, text=True, timeout=30).stdout.strip()
if not KEY:
    sys.exit("kein Key")
UP = ("127.0.0.1", 28765)
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
       "transfer-encoding", "upgrade", "host", "content-length"}


class H(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _go(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n) if n else None
        h = {k: v for k, v in self.headers.items() if k.lower() not in HOP | {"origin", "remote-user", "x-ma-key", "x-ma-request"}}
        h.update({"X-MA-Key": KEY, "Remote-User": "andrew", "Origin": "https://ma-server.duckdns.org", "X-MA-Request": "1"})
        c = http.client.HTTPConnection(*UP, timeout=120)
        c.request(self.command, self.path, body=body, headers=h)
        r = c.getresponse()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in HOP:
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        while True:
            b = r.read(4096)
            if not b:
                break
            self.wfile.write(("%x\r\n" % len(b)).encode() + b + b"\r\n")
            self.wfile.flush()
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = _go


class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


print("Proxy bereit auf 127.0.0.1:28766", flush=True)
S(("127.0.0.1", 28766), H).serve_forever()
