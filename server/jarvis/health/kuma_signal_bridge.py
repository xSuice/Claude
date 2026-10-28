"""Uptime-Kuma webhook -> Signal (own account, self-chat). Loopback only, shared token header, rate limited.
Never logs message bodies, numbers or tokens. Runs as user service ma-kuma-signal (andrew)."""
import hmac, json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, '/opt/jarvis/council')
from signal_push import send  # noqa: E402

HOME = os.path.expanduser('~')
TOKEN_FILE = os.path.join(HOME, '.config/ma-jarvis/kuma-bridge-token')
ACCOUNTS = os.path.join(HOME, '.local/share/ma-jarvis/signal/account/data/accounts.json')
PORT = int(os.environ.get('MA_KUMA_BRIDGE_PORT', '18772'))
MIN_GAP = 600          # s: hoechstens eine Meldung je Monitor und Zustand alle 10 min
_last = {}


def token():
    with open(TOKEN_FILE, encoding='utf-8') as f:
        return f.read().strip()


def account():
    accounts = json.load(open(ACCOUNTS))['accounts']
    if len(accounts) != 1:
        raise RuntimeError('Expected exactly one Signal account')
    return accounts[0]['number']


def render(payload):
    """Kuma webhook JSON -> (key, title, text) or None. Status 0 = down, 1 = up."""
    hb = payload.get('heartbeat') or {}
    mon = payload.get('monitor') or {}
    name = str(mon.get('name') or 'Dienst')[:60]
    if not hb:   # Testnachricht aus der Kuma-Oberflaeche
        return ('test', 'Statusmonitor', 'Testmeldung von Uptime Kuma: Signal-Weiterleitung funktioniert.')
    status = hb.get('status')
    if status not in (0, 1):
        return None
    detail = str(hb.get('msg') or '')[:160]
    if status == 0:
        return (name + ':down', 'Dienst ausgefallen: ' + name, ('Grund: ' + detail) if detail else 'Keine Antwort.')
    return (name + ':up', 'Dienst wieder da: ' + name, 'Läuft wieder.')


def allowed(key, now=None):
    now = time.time() if now is None else now
    if now - _last.get(key, 0) < MIN_GAP:
        return False
    _last[key] = now
    return True


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _reply(self, code):
        self.send_response(code)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        if self.path != '/kuma' or not hmac.compare_digest(self.headers.get('X-Bridge-Token', ''), token()):
            return self._reply(403)
        n = int(self.headers.get('Content-Length') or 0)
        if n <= 0 or n > 64 * 1024:
            return self._reply(413)
        try:
            item = render(json.loads(self.rfile.read(n)))
        except (ValueError, TypeError):
            return self._reply(400)
        if item is None or not allowed(item[0]):
            return self._reply(204)
        try:
            send({'title': item[1], 'message': item[2]}, account())
        except Exception:
            print(time.strftime('%F %T'), 'signal delivery failed', flush=True)
            return self._reply(502)
        print(time.strftime('%F %T'), 'sent', item[0].split(':')[-1], flush=True)
        return self._reply(204)


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
