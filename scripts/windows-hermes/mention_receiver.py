#!/usr/bin/env python3
"""Mention-Receiver: Endpunkt fuer den Server-seitigen chat_bus mention_poller.

Empfaengt POST /api/bot/dm {"target": "<profil>", "message": "..."} vom
Reverse-Tunnel (ma-server:8484 -> hier:8484) und deliveriert die Nachricht
als User-Turn in das "Bot Chat" des Ziel-Profils (gleicher Mechanismus wie
bot_mode_dm.py: hermes -p <ziel> chat --in ~ -c "Bot Chat" -Q <text>).

Nur 127.0.0.1, kein Shell-Einsatz (argv-Liste), Zielnamen-Validierung.
"""
import json
import logging
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERMES_ROOT = Path(__file__).resolve().parent.parent  # C:/Users/andre/AppData/Local/hermes
LISTEN = ("127.0.0.1", 8484)
HERMES = HERMES_ROOT / "hermes-agent" / ".hermes" / "bin" / "hermes.exe"
PROFILES = HERMES_ROOT / "profiles"
LOG = Path(__file__).resolve().parent / "mention_receiver.log"
TARGET_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAX_MSG = 8000

logging.basicConfig(
    filename=LOG, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def valid_target(name: str) -> bool:
    if not TARGET_RE.match(name or ""):
        return False
    return (PROFILES / name).is_dir()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # stilllegen -> logging oben
        logging.info("http " + fmt % args)

    def _send(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") != "/api/bot/dm":
            return self._send(404, {"error": "not found"})
        try:
            length = min(int(self.headers.get("Content-Length", "0")), MAX_MSG + 4096)
            data = json.loads(self.rfile.read(length))
        except Exception:
            return self._send(400, {"error": "invalid json"})
        target = str(data.get("target", "")).strip().lower()
        message = str(data.get("message", "")).strip()[:MAX_MSG]
        if not message:
            return self._send(400, {"error": "empty message"})
        if not valid_target(target):
            logging.warning("reject target=%r", target)
            return self._send(404, {"error": f"unknown target {target!r}"})
        try:
            subprocess.Popen(
                [str(HERMES), "-p", target, "chat", "--in", "~",
                 "-c", "Bot Chat", "--create-if-missing", "-Q", message],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                cwd=str(PROFILES / target),
            )
        except Exception as exc:
            logging.error("deliver %s failed: %s", target, exc)
            return self._send(500, {"error": str(exc)})
        logging.info("delivered target=%s msg=%.80r", target, message)
        self._send(202, {"status": "queued", "target": target})

    def do_GET(self):
        if self.path.rstrip("/") == "/healthz":
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})


def main():
    if not HERMES.is_file():
        print(f"hermes CLI fehlt: {HERMES}", file=sys.stderr)
        sys.exit(2)
    srv = ThreadingHTTPServer(LISTEN, Handler)
    logging.info("mention_receiver auf %s:%d bereit", *LISTEN)
    print(f"mention_receiver auf http://{LISTEN[0]}:{LISTEN[1]} bereit")
    srv.serve_forever()


if __name__ == "__main__":
    main()
